from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from bleak.exc import BleakError
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from bleak_retry_connector import (
    BleakAbortedError,
    BleakClientWithServiceCache,
    BleakConnectionError,
    BleakNotFoundError,
    BleakOutOfConnectionSlotsError,
    establish_connection,
)

from .const import (
    DOMAIN,
    CONF_ADDRESS,
    CONF_ALARM_ON_DISCONNECT,
    CONF_AUTO_RECONNECT,
    CONF_BATTERY_POLL_INTERVAL_MIN,
    CONF_MAINTAIN_CONNECTION,
    CONF_NAME,
    DEFAULT_ALARM_ON_DISCONNECT,
    DEFAULT_AUTO_RECONNECT,
    DEFAULT_BATTERY_POLL_INTERVAL_MIN,
    DEFAULT_MAINTAIN_CONNECTION,
    UUID_ALERT_LEVEL_2A06,
    UUID_BATTERY_LEVEL_2A19,
    UUID_NOTIFY_FFE1,
    UUID_WRITE_FFE2,
)

_LOGGER = logging.getLogger(__name__)

_UUID_SERVICE_IMMEDIATE_ALERT_1802 = "00001802-0000-1000-8000-00805f9b34fb"
_UUID_SERVICE_BATTERY_180F = "0000180f-0000-1000-8000-00805f9b34fb"


@dataclass
class ButtonEvent:
    when: datetime
    raw: bytes


class AntiLossTagDevice:
    """Device/session manager for a single BLE anti-loss tag."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

        self.address: str = entry.data[CONF_ADDRESS]
        self.name: str = entry.data.get(CONF_NAME) or self.address

        self._available: bool = False
        self._connected: bool = False
        self._rssi: int | None = None
        self._last_seen: datetime | None = None

        self._battery: int | None = None
        self._last_battery_read: datetime | None = None

        self._last_button_event: ButtonEvent | None = None

        self._client: BleakClientWithServiceCache | None = None
        self._connect_lock = asyncio.Lock()
        self._gatt_lock = asyncio.Lock()

        self._cancel_bt_callback: Callable[[], None] | None = None
        self._cancel_unavailable: Callable[[], None] | None = None

        self._listeners: set[Callable[[], None]] = set()
        self._button_listeners: set[Callable[[ButtonEvent], None]] = set()

        self._connect_task: asyncio.Task | None = None
        self._battery_task: asyncio.Task | None = None

        self._last_error: str | None = None

        # ====== 多设备并发连接控制（全局连接槽位 + 退避） ======
        try:
            self._conn_mgr = self.hass.data[DOMAIN].get("_conn_mgr")
        except Exception:  # noqa: BLE001
            self._conn_mgr = None

        self._conn_slot_acquired: bool = False
        self._connect_fail_count: int = 0
        self._cooldown_until_ts: float = 0.0

        # 用于解决“同 UUID 多特征”的歧义：优先解析并缓存 handle
        self._alert_level_handle: int | None = None
        self._battery_level_handle: int | None = None

    # -------------------------
    # Public read-only state
    # -------------------------
    @property
    def available(self) -> bool:
        return self._available

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def rssi(self) -> int | None:
        return self._rssi

    @property
    def last_seen(self) -> datetime | None:
        return self._last_seen

    @property
    def battery(self) -> int | None:
        return self._battery

    @property
    def last_battery_read(self) -> datetime | None:
        return self._last_battery_read

    @property
    def last_button_event(self) -> ButtonEvent | None:
        return self._last_button_event

    @property
    def last_error(self) -> str | None:
        return self._last_error

    # -------------------------
    # Options
    # -------------------------
    def _opt_bool(self, key: str, default: bool) -> bool:
        return bool(self.entry.options.get(key, default))

    def _opt_int(self, key: str, default: int) -> int:
        try:
            return int(self.entry.options.get(key, default))
        except (ValueError, TypeError):
            return default

    @property
    def alarm_on_disconnect(self) -> bool:
        return self._opt_bool(CONF_ALARM_ON_DISCONNECT, DEFAULT_ALARM_ON_DISCONNECT)

    @property
    def maintain_connection(self) -> bool:
        return self._opt_bool(CONF_MAINTAIN_CONNECTION, DEFAULT_MAINTAIN_CONNECTION)

    @property
    def auto_reconnect(self) -> bool:
        return self._opt_bool(CONF_AUTO_RECONNECT, DEFAULT_AUTO_RECONNECT)

    @property
    def battery_poll_interval_min(self) -> int:
        return self._opt_int(CONF_BATTERY_POLL_INTERVAL_MIN, DEFAULT_BATTERY_POLL_INTERVAL_MIN)

    # -------------------------
    # Lifecycle
    # -------------------------
    def async_start(self) -> None:
        """Start Bluetooth subscriptions and background tasks."""
        if self._cancel_bt_callback is None:
            self._cancel_bt_callback = bluetooth.async_register_callback(
                self.hass,
                self._async_on_bluetooth_event,
                {"address": self.address},
                bluetooth.BluetoothScanningMode.ACTIVE,
            )

        if self._cancel_unavailable is None:
            self._cancel_unavailable = bluetooth.async_track_unavailable(
                self.hass,
                self._async_on_unavailable,
                self.address,
                connectable=True,
            )

        self._ensure_battery_task()

    def async_stop(self) -> None:
        """Stop tasks, callbacks and disconnect."""
        if self._cancel_bt_callback is not None:
            self._cancel_bt_callback()
            self._cancel_bt_callback = None

        if self._cancel_unavailable is not None:
            self._cancel_unavailable()
            self._cancel_unavailable = None

        if self._battery_task is not None:
            self._battery_task.cancel()
            self._battery_task = None

        if self._connect_task is not None:
            self._connect_task.cancel()
            self._connect_task = None

        self.hass.async_create_task(self.async_disconnect())

    async def async_apply_entry_options(self) -> None:
        """Apply updated options (called from update listener)."""
        # If maintain_connection toggled on, attempt to connect when available
        if self.maintain_connection:
            self._ensure_connect_task()
        else:
            # If user disables maintain_connection, we can disconnect to free slots
            await self.async_disconnect()

        # Always re-sync policy when we are connected (or will be shortly)
        if self.maintain_connection:
            self._ensure_connect_task()
        else:
            # If not maintaining, best-effort short connect to sync policy
            await self.async_set_disconnect_alarm_policy(self.alarm_on_disconnect, force_connect=True)

        # Battery task interval changed, restart loop task
        self._ensure_battery_task(restart=True)

    async def async_maybe_connect_initial(self) -> None:
        """Initial connect attempt after setup."""
        if not self.maintain_connection:
            return
        # If device is already present, connect; else wait for advertisements
        if bluetooth.async_address_present(self.hass, self.address, connectable=True):
            self._ensure_connect_task()

    # -------------------------
    # Listener registration
    # -------------------------
    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(listener)

        @callback
        def _remove() -> None:
            self._listeners.discard(listener)

        return _remove

    @callback
    def async_add_button_listener(self, listener: Callable[[ButtonEvent], None]) -> Callable[[], None]:
        self._button_listeners.add(listener)

        @callback
        def _remove() -> None:
            self._button_listeners.discard(listener)

        return _remove

    @callback
    def _async_dispatch_update(self) -> None:
        for listener in list(self._listeners):
            listener()

    @callback
    def _async_dispatch_button(self, event: ButtonEvent) -> None:
        for listener in list(self._button_listeners):
            listener(event)

    # -------------------------
    # Bluetooth callbacks
    # -------------------------
    @callback
    def _async_on_bluetooth_event(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle advertisement updates."""
        self._available = True
        self._rssi = service_info.rssi
        self._last_seen = datetime.now(timezone.utc)

        self._async_dispatch_update()

        if self.maintain_connection and not self._connected:
            self._ensure_connect_task()

    @callback
    def _async_on_unavailable(self, info: bluetooth.BluetoothServiceInfoBleak) -> None:
        """Handle device no longer seen (may take time to trigger)."""
        self._available = False
        self._async_dispatch_update()

        # If we lose advertisements, the connection likely isn't valid anymore
        if self._connected and self.auto_reconnect:
            self._ensure_connect_task()

    # -------------------------
    # Connection management
    # -------------------------
    def _ensure_connect_task(self) -> None:
        if self._connect_task is not None and not self._connect_task.done():
            return
        self._connect_task = self.hass.async_create_task(self.async_ensure_connected())

    def _ensure_battery_task(self, restart: bool = False) -> None:
        if restart and self._battery_task is not None:
            self._battery_task.cancel()
            self._battery_task = None
        if self._battery_task is None or self._battery_task.done():
            self._battery_task = self.hass.async_create_task(self._async_battery_loop())

    def _ble_device_callback(self):
        return bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )

    def _on_disconnect(self, _client) -> None:
        self._connected = False

        # ====== 断开：归还全局连接槽位 ======
        if self._conn_mgr is not None and self._conn_slot_acquired:
            self.hass.async_create_task(self._conn_mgr.release())
            self._conn_slot_acquired = False
        # ====== 结束 ======
        self._client = None
        self._alert_level_handle = None
        self._battery_level_handle = None
        self._async_dispatch_update()

        if self.auto_reconnect and self.maintain_connection:
            self._ensure_connect_task()

    async def async_ensure_connected(self) -> None:
        """没有可连接的 BLEDevice（可能超出范围或没有可连接的扫描器）。"""
        async with self._connect_lock:
            # ====== 连接退避：避免多设备同时冲连接 ======
            import time
            now_ts = time.time()
            if now_ts < self._cooldown_until_ts:
                return
            if self._connected and self._client is not None:
                return

            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if ble_device is None:
                self._last_error = "No connectable BLEDevice available (out of range or no connectable scanner)."
                self._connected = False
                self._client = None

            # ====== 主动断开：归还全局连接槽位 ======
            if self._conn_mgr is not None and self._conn_slot_acquired:
                await self._conn_mgr.release()
                self._conn_slot_acquired = False
            # ====== 结束 ======
                self._async_dispatch_update()
                return

            # ====== 获取全局连接槽位（跨设备并发控制） ======
            if self._conn_mgr is not None and not self._conn_slot_acquired:
                acq = await self._conn_mgr.acquire(timeout=20.0)
                if not acq.acquired:
                    self._connect_fail_count = min(self._connect_fail_count + 1, 6)
                    backoff = min(30, (2 ** self._connect_fail_count))
                    import time
                    self._cooldown_until_ts = time.time() + backoff
                    self._last_error = f"等待连接槽位中({acq.reason}); {backoff}s 后重试"
                    self._connected = False
                    self._client = None
                    self._async_dispatch_update()
                    return
                self._conn_slot_acquired = True
            # ====== 结束 ======

            try:
                client: BleakClientWithServiceCache = await establish_connection(
                    BleakClientWithServiceCache,
                    ble_device,
                    self.name,
                    disconnected_callback=self._on_disconnect,
                    ble_device_callback=self._ble_device_callback,
                )
            except (BleakOutOfConnectionSlotsError, BleakNotFoundError, BleakAbortedError, BleakConnectionError) as err:
                # ====== 连接失败：归还全局连接槽位 + 退避 ======
                if self._conn_mgr is not None and self._conn_slot_acquired:
                    await self._conn_mgr.release()
                    self._conn_slot_acquired = False
                self._connect_fail_count = min(self._connect_fail_count + 1, 6)
                backoff = min(60, (2 ** self._connect_fail_count))
                import time
                self._cooldown_until_ts = time.time() + backoff
                # ====== 结束 ======
                self._last_error = f"连接失败: {err}"
                self._connected = False
                self._client = None
                self._async_dispatch_update()
                return
            except Exception as err:  # safety net
                self._last_error = f"连接失败（异常）: {err}"
                self._connected = False
                self._client = None
                self._async_dispatch_update()
                return

            self._client = client
            self._connected = True
            # ====== 连接成功：重置退避 ======
            self._connect_fail_count = 0
            self._cooldown_until_ts = 0.0
            # ====== 结束 ======
            self._last_error = None
            self._async_dispatch_update()

            # Ensure services are discovered
            try:
                await client.get_services()
            except Exception as err:
                # ====== 连接失败：归还全局连接槽位 + 退避 ======
                if self._conn_mgr is not None and self._conn_slot_acquired:
                    await self._conn_mgr.release()
                    self._conn_slot_acquired = False
                self._connect_fail_count = min(self._connect_fail_count + 1, 6)
                backoff = min(60, (2 ** self._connect_fail_count))
                import time
                self._cooldown_until_ts = time.time() + backoff
                # ====== 结束 ======
                self._last_error = f"服务发现失败: {err}"
                self._async_dispatch_update()

            # Resolve duplicated characteristic UUIDs to unique handles (best-effort)
            try:
                self._resolve_gatt_handles()
            except Exception as err:
                _LOGGER.debug("Resolve GATT handles failed: %s", err)

            # Enable notifications (FFE1) best-effort
            await self._async_enable_notifications()

            # Sync disconnect alarm policy (FFE2) best-effort
            await self.async_set_disconnect_alarm_policy(self.alarm_on_disconnect, force_connect=False)

            # Read battery once on connect (best-effort)
            await self.async_read_battery(force_connect=False)

    async def async_disconnect(self) -> None:
        async with self._connect_lock:
            if self._client is None:
                self._connected = False
                self._async_dispatch_update()
                return
            try:
                try:
                    await self._client.stop_notify(UUID_NOTIFY_FFE1)
                except Exception:
                    pass
                await self._client.disconnect()
            finally:
                self._client = None
                self._connected = False
                self._alert_level_handle = None
                self._battery_level_handle = None
                self._async_dispatch_update()

    async def _async_enable_notifications(self) -> None:
        client = self._client
        if client is None:
            return

        async def _handler(_sender: int, data: bytearray) -> None:
            raw = bytes(data)
            if not raw:
                return
            # Follow your Android behavior: first byte == 1 -> treat as button press
            if raw[0] == 1:
                event = ButtonEvent(when=datetime.now(timezone.utc), raw=raw)
                self._last_button_event = event
                self._async_dispatch_button(event)
                self._async_dispatch_update()

        try:
            await client.start_notify(UUID_NOTIFY_FFE1, _handler)
        except BleakError as err:
            self._last_error = f"开启通知(FFE1)失败: {err}"
            self._async_dispatch_update()
        except Exception as err:
            self._last_error = f"开启通知(FFE1)失败（异常）: {err}"
            self._async_dispatch_update()

    # -------------------------
    # Characteristic handle resolution
    # -------------------------
    def _normalize_uuid(self, u: str) -> str:
        return u.strip().lower()

    def _resolve_char_handle(
        self,
        char_uuid: str,
        *,
        preferred_service_uuid: str | None = None,
        require_write: bool = False,
    ) -> int | None:
        client = self._client
        if client is None:
            return None

        services = getattr(client, "services", None)
        if services is None:
            return None

        cu = self._normalize_uuid(char_uuid)
        psu = self._normalize_uuid(preferred_service_uuid) if preferred_service_uuid else None

        matches: list[tuple[str, object]] = []
        for svc in services:
            svc_uuid = self._normalize_uuid(getattr(svc, "uuid", ""))
            for ch in getattr(svc, "characteristics", []) or []:
                if self._normalize_uuid(getattr(ch, "uuid", "")) == cu:
                    matches.append((svc_uuid, ch))

        if not matches:
            return None

        def _is_writable(ch: object) -> bool:
            props = getattr(ch, "properties", []) or []
            props_l = {str(p).lower() for p in props}
            return ("write" in props_l) or ("write-without-response" in props_l)

        if len(matches) > 1 and psu:
            preferred = [(s, ch) for (s, ch) in matches if s == psu]
            if preferred:
                matches = preferred

        if require_write:
            writable = [(s, ch) for (s, ch) in matches if _is_writable(ch)]
            if writable:
                matches = writable

        if len(matches) > 1:
            handles = []
            for svc_uuid, ch in matches:
                try:
                    handles.append((svc_uuid, int(getattr(ch, "handle"))))
                except Exception:
                    handles.append((svc_uuid, None))
            _LOGGER.warning(
                "Multiple characteristics for UUID %s; selecting the first by handle. Candidates=%s",
                char_uuid,
                handles,
            )

        try:
            return int(getattr(matches[0][1], "handle"))
        except Exception:
            return None

    def _resolve_gatt_handles(self) -> None:
        self._alert_level_handle = self._resolve_char_handle(
            UUID_ALERT_LEVEL_2A06,
            preferred_service_uuid=_UUID_SERVICE_IMMEDIATE_ALERT_1802,
            require_write=True,
        )
        self._battery_level_handle = self._resolve_char_handle(
            UUID_BATTERY_LEVEL_2A19,
            preferred_service_uuid=_UUID_SERVICE_BATTERY_180F,
            require_write=False,
        )

    # -------------------------
    # GATT operations
    # -------------------------
    async def async_start_alarm(self) -> None:
        char = self._alert_level_handle if self._alert_level_handle is not None else UUID_ALERT_LEVEL_2A06
        await self._async_write_bytes(char, bytes([0x01]), prefer_response=False)

    async def async_stop_alarm(self) -> None:
        char = self._alert_level_handle if self._alert_level_handle is not None else UUID_ALERT_LEVEL_2A06
        await self._async_write_bytes(char, bytes([0x00]), prefer_response=False)

    async def async_set_disconnect_alarm_policy(self, enabled: bool, force_connect: bool) -> None:
        value = bytes([0x01 if enabled else 0x00])
        if self._client is None and force_connect:
            await self.async_ensure_connected()
            # If user does not want to maintain connection, disconnect afterwards
            if not self.maintain_connection:
                try:
                    await self._async_write_bytes(UUID_WRITE_FFE2, value, prefer_response=True)
                finally:
                    await self.async_disconnect()
                return
        await self._async_write_bytes(UUID_WRITE_FFE2, value, prefer_response=True)

    async def async_read_battery(self, force_connect: bool) -> None:
        if self._client is None:
            if not force_connect:
                return
            await self.async_ensure_connected()
            if self._client is None:
                return

        async with self._gatt_lock:
            client = self._client
            if client is None:
                return
            try:
                char = self._battery_level_handle if self._battery_level_handle is not None else UUID_BATTERY_LEVEL_2A19
                # ====== 多特征同 UUID：电量读取按 handle 重试 ======
                try:
                    data = await client.read_gatt_char(char)
                except BleakError as err:
                    if isinstance(char, str) and "Multiple Characteristics with this UUID" in str(err):
                        try:
                            await client.get_services()
                        except Exception:
                            pass
                        handle = self._resolve_char_handle(
                            char,
                            preferred_service_uuid=_UUID_SERVICE_BATTERY_180F,
                            require_write=False,
                        )
                        if handle is not None:
                            data = await client.read_gatt_char(handle)
                        else:
                            raise
                    else:
                        raise
                # ====== 结束 ======
                if data and len(data) >= 1:
                    level = int(data[0])
                    level = max(0, min(100, level))
                    self._battery = level
                    self._last_battery_read = datetime.now(timezone.utc)
                    self._async_dispatch_update()
            except BleakError as err:
                self._last_error = f"读取电量失败: {err}"
                self._async_dispatch_update()
            except Exception as err:
                self._last_error = f"读取电量失败（异常）: {err}"
                self._async_dispatch_update()

    async def _async_write_bytes(self, uuid: str | int, data: bytes, prefer_response: bool) -> None:
        if self._client is None:
            # If we maintain connection, schedule connect then retry once
            if self.maintain_connection:
                await self.async_ensure_connected()
            else:
                # For on-demand mode, connect transiently just for this write
                await self.async_ensure_connected()
                if self._client is None:
                    raise BleakError("没有可用的 BLE 客户端用于写入")

        async with self._gatt_lock:
            client = self._client
            if client is None:
                raise BleakError("没有可用的 BLE 客户端用于写入")

            # ====== 多特征同 UUID：按 handle 重试（兼容 bleak 报错） ======
            async def _resolve_handle_for_uuid(u: str) -> int | None:
                # 2A06（报警）通常在 1802 Immediate Alert 服务下；其余默认不限定服务
                preferred = _UUID_SERVICE_IMMEDIATE_ALERT_1802 if u.lower() == UUID_ALERT_LEVEL_2A06.lower() else None
                return self._resolve_char_handle(u, preferred_service_uuid=preferred, require_write=True)

            async def _write_with_possible_handle_retry(resp: bool) -> None:
                try:
                    await client.write_gatt_char(uuid, data, response=resp)
                    return
                except BleakError as err:
                    if isinstance(uuid, str) and "Multiple Characteristics with this UUID" in str(err):
                        try:
                            await client.get_services()
                        except Exception:
                            pass
                        handle = _resolve_handle_for_uuid(uuid)
                        if handle is not None:
                            await client.write_gatt_char(handle, data, response=resp)
                            return
                    raise
            # ====== 结束 ======

            # Try preferred response mode first, then fallback
            try:
                await _write_with_possible_handle_retry(prefer_response)
                return
            except Exception:
                pass

            try:
                await _write_with_possible_handle_retry(not prefer_response)
            except Exception as err:
                self._last_error = f"写入 {uuid} 失败: {err}"
                self._async_dispatch_update()
                raise

    async def _async_battery_loop(self) -> None:
        while True:
            try:
                # ====== 抖动（避免多设备同时轮询） ======
                import random
                base = self.battery_poll_interval_min * 60
                jitter = random.randint(0, 30)  # 0~30s
                await asyncio.sleep(base + jitter)
                # ====== 结束 ======
                await self.async_read_battery(force_connect=not self.maintain_connection)
            except asyncio.CancelledError:
                return
            except Exception as err:
                self._last_error = f"电量轮询异常: {err}"
                self._async_dispatch_update()
