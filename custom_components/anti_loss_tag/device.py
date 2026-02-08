# SPDX-License-Identifier: MIT
# Copyright (c) 2025-2026 MMMM
# See LICENSE file for details
from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, cast

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak import BleakClient
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
from .connection_manager import BleConnectionManager
from .utils.constants import (
    BATTERY_POLL_JITTER_SECONDS,
    MAX_CONNECT_BACKOFF_SECONDS,
    MAX_CONNECT_FAIL_COUNT,
    CONNECTION_SLOT_ACQUIRE_TIMEOUT,
    ENTITY_UPDATE_DEBOUNCE_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

_UUID_SERVICE_IMMEDIATE_ALERT_1802 = "00001802-0000-1000-8000-00805f9b34fb"
_UUID_SERVICE_BATTERY_180F = "0000180f-0000-1000-8000-00805f9b34fb"


@dataclass
class ButtonEvent:
    when: datetime
    raw: bytes


@dataclass
class DeviceOperation:
    """串行化设备操作任务。"""

    name: str
    action: Callable[[], Awaitable[Any]]
    retries: int
    retry_delay: float
    future: asyncio.Future[Any]


class AntiLossTagDevice:
    """KT6368A芯片专用设备管理器。

    本类专门管理基于KT6368A双模蓝牙5.1 SoC的防丢标签设备，
    实现基于BLE核心规范和KT6368A芯片规格文档。

    技术标准参考：
    - BLE Specification: Bluetooth Core Specification 5.1
    - 芯片规格: KT6368A双模蓝牙5.1 SoC（SOP-8封装）
    - 架构分析：docs/BLE技术指南/BLE通信架构分析.md
    - 开发指南：docs/BLE技术指南/Python_BLE开发指南.md

    协议特性（FFE0服务 - KT6368A定制）：
    - FFE0: 服务UUID（设备扫描和识别）
    - FFE1: 通知特征（按键事件实时上报，字节流格式）
    - FFE2: 写入特征（断开报警策略同步）
    - 2A06: Alert Level特征（即时报警：0x01=响铃，0x00=停止）
    - 2A19: Battery Level特征（电量读取：0-100%）
    """

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

        # ====== GATT特征缓存（从device/gatt_operations.py集成） ======
        # 缓存BleakGATTCharacteristic对象，避免重复UUID查找
        self._cached_chars: dict[str, BleakGATTCharacteristic] = {}

        self._listeners: set[Callable[[], None]] = set()
        self._button_listeners: set[Callable[[ButtonEvent], None]] = set()

        self._connect_task: asyncio.Task | None = None
        self._battery_task: asyncio.Task | None = None
        self._op_worker_task: asyncio.Task | None = None
        self._op_queue: asyncio.PriorityQueue[tuple[int, int, DeviceOperation]] = (
            asyncio.PriorityQueue()
        )
        self._op_seq: int = 0
        self._battery_read_lock = asyncio.Lock()

        self._last_error: str | None = None

        # ====== 实体更新防抖动（避免频繁更新） ======
        self._last_update_time: float = 0.0

        # ====== 多设备并发连接控制（全局连接槽位 + 退避） ======
        try:
            self._conn_mgr: BleConnectionManager | None = cast(
                BleConnectionManager | None,
                self.hass.data[DOMAIN].get("_conn_mgr"),
            )
        except (KeyError, AttributeError) as err:
            _LOGGER.debug("Connection manager not available: %s", err)
            self._conn_mgr = None

        self._conn_slot_acquired: bool = False
        self._connect_fail_count: int = 0
        self._cooldown_until_ts: float = 0.0

        # 用于解决"同 UUID 多特征"的歧义：优先解析并缓存 handle
        self._alert_level_handle: int | None = None
        self._battery_level_handle: int | None = None

        # 对齐 HA IQS log-when-unavailable：避免重复记录不可用日志
        self._unavailability_logged: bool = False

        # 连接失败分类（用于诊断和重试决策）
        self._connection_error_classification: str | None = None
        self._connection_error_type: str | None = None
        self._last_connect_attempt: datetime | None = None
        self._connection_state: str = "idle"

        self._last_operation_error: str | None = None

        self._op_priority_alarm = 10
        self._op_priority_policy = 20
        self._op_priority_battery = 50
        self._last_alarm_operation_ts: float = 0.0
        self._battery_defer_count: int = 0
        self._last_battery_sleep_seconds: float = 0.0
        self._last_battery_sleep_reason: str = "init"
        self._adaptive_mode: str = "normal"
        self._adaptive_timeout_ratio: float = 0.0

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

    @property
    def connection_state(self) -> str:
        return self._connection_state

    @property
    def connection_error_classification(self) -> str | None:
        return self._connection_error_classification

    @property
    def connection_error_type(self) -> str | None:
        return self._connection_error_type

    @property
    def operation_queue_size(self) -> int:
        return self._op_queue.qsize()

    @property
    def operation_worker_running(self) -> bool:
        return self._op_worker_task is not None and not self._op_worker_task.done()

    @property
    def last_operation_error(self) -> str | None:
        return self._last_operation_error

    @property
    def battery_defer_count(self) -> int:
        return self._battery_defer_count

    @property
    def last_battery_sleep_seconds(self) -> float:
        return self._last_battery_sleep_seconds

    @property
    def last_battery_sleep_reason(self) -> str:
        return self._last_battery_sleep_reason

    @property
    def battery_read_busy(self) -> bool:
        return self._battery_read_lock.locked()

    @property
    def adaptive_mode(self) -> str:
        return self._adaptive_mode

    @property
    def adaptive_timeout_ratio(self) -> float:
        return self._adaptive_timeout_ratio

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
        return self._opt_int(
            CONF_BATTERY_POLL_INTERVAL_MIN, DEFAULT_BATTERY_POLL_INTERVAL_MIN
        )

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
        self._ensure_operation_worker()

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

        if self._op_worker_task is not None:
            self._op_worker_task.cancel()
            self._op_worker_task = None

        self._clear_operation_queue()

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
            await self.async_set_disconnect_alarm_policy(
                self.alarm_on_disconnect, force_connect=True
            )

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
    def async_add_button_listener(
        self, listener: Callable[[ButtonEvent], None]
    ) -> Callable[[], None]:
        self._button_listeners.add(listener)

        @callback
        def _remove() -> None:
            self._button_listeners.discard(listener)

        return _remove

    @callback
    def _async_dispatch_update(self) -> None:
        """Dispatch update to all listeners with debouncing."""
        # ====== 防抖动（避免频繁更新） ======
        now = time.time()
        if now - self._last_update_time < ENTITY_UPDATE_DEBOUNCE_SECONDS:
            _LOGGER.debug(
                "Update debounced (last %.2fs ago)", now - self._last_update_time
            )
            return
        self._last_update_time = now
        # ====== 结束 ======

        for listener in list(self._listeners):
            listener()

    @callback
    def _async_dispatch_button(self, event: ButtonEvent) -> None:
        for listener in list(self._button_listeners):
            listener(event)

    # -------------------------
    # Bluetooth callbacks
    # -------------------------
    def _update_availability(self, available: bool) -> None:
        """Update device availability state (single entry point).

        This is the only method that should modify _available, ensuring
        consistency and making it easier to track availability changes.

        Args:
            available: True if device is available, False otherwise
        """
        if self._available != available:
            self._available = available
            _LOGGER.debug(
                "Device %s availability changed: %s",
                self.address,
                "AVAILABLE" if available else "UNAVAILABLE",
            )

    @callback
    def _async_on_bluetooth_event(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle advertisement updates."""
        self._update_availability(True)
        self._rssi = service_info.rssi
        self._last_seen = datetime.now(timezone.utc)

        self._async_dispatch_update()

        if self.maintain_connection and not self._connected:
            self._ensure_connect_task()

    @callback
    def _async_on_unavailable(self, info: bluetooth.BluetoothServiceInfoBleak) -> None:
        """Handle device no longer seen (may take time to trigger)."""
        self._update_availability(False)
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

    def _ensure_operation_worker(self) -> None:
        if self._op_worker_task is not None and not self._op_worker_task.done():
            return
        self._op_worker_task = self.hass.async_create_task(
            self._async_operation_worker()
        )

    def _clear_operation_queue(self) -> None:
        while True:
            try:
                _, _, op = self._op_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            if not op.future.done():
                op.future.cancel()
            self._op_queue.task_done()

    async def _async_enqueue_operation(
        self,
        *,
        name: str,
        action: Callable[[], Awaitable[Any]],
        priority: int,
        retries: int = 0,
        retry_delay: float = 0.8,
    ) -> Any:
        self._ensure_operation_worker()
        self._op_seq += 1
        future: asyncio.Future[Any] = self.hass.loop.create_future()
        op = DeviceOperation(
            name=name,
            action=action,
            retries=max(0, retries),
            retry_delay=max(0.0, retry_delay),
            future=future,
        )
        await self._op_queue.put((priority, self._op_seq, op))
        return await future

    def _is_retryable_operation_error(self, err: Exception) -> bool:
        classification = self._connection_error_classification
        if classification in {"slot_timeout", "connect_error", "scanner_unavailable"}:
            return True
        return isinstance(err, (TimeoutError, OSError))

    def _compute_slot_acquire_timeout(self, *, connect_purpose: str) -> float:
        timeout = float(CONNECTION_SLOT_ACQUIRE_TIMEOUT)
        if connect_purpose == "background_battery":
            timeout = min(timeout, 6.0)
        elif connect_purpose in {"interactive_alarm", "policy_sync"}:
            timeout = max(timeout, 25.0)

        conn_mgr = self._conn_mgr
        if conn_mgr is not None:
            try:
                if conn_mgr.in_use >= conn_mgr.max_connections:
                    if connect_purpose == "background_battery":
                        timeout = min(timeout, 4.0)
                    else:
                        timeout = min(30.0, timeout + 5.0)

                # 若近期超时率高，后台任务更快放弃，前台任务适当增加等待
                if conn_mgr.acquire_total >= 10:
                    timeout_ratio = conn_mgr.acquire_timeout / conn_mgr.acquire_total
                    self._adaptive_timeout_ratio = timeout_ratio
                    if timeout_ratio >= 0.4:
                        self._adaptive_mode = "timeout_high"
                        if connect_purpose == "background_battery":
                            timeout = min(timeout, 3.0)
                        else:
                            timeout = min(30.0, timeout + 4.0)
                    else:
                        self._adaptive_mode = "normal"
            except (AttributeError, TypeError):
                pass

        return timeout

    def _should_defer_battery_poll(self) -> bool:
        # 已连接时读取电量不需要再争抢连接槽位，不应被延后
        if self._connected and self._client is not None:
            return False

        # 优先保障用户触发的报警操作
        if self._op_queue.qsize() > 0:
            return True

        # 报警操作后的短窗口内，暂缓后台轮询
        now_ts = time.monotonic()
        if (now_ts - self._last_alarm_operation_ts) < 8.0:
            return True

        # 全局连接槽位接近占满时，暂缓低优先级电量轮询
        if self._conn_mgr is not None:
            try:
                if self._conn_mgr.in_use >= self._conn_mgr.max_connections:
                    return True
            except (AttributeError, TypeError):
                return False

        return False

    def _compute_next_battery_sleep_seconds(
        self, *, force_connect: bool
    ) -> tuple[float, str]:
        if self._op_queue.qsize() >= 3:
            self._adaptive_mode = "queue_busy"
            return (120.0, "queue_busy")

        conn_mgr = self._conn_mgr
        if conn_mgr is not None:
            try:
                if conn_mgr.average_wait_ms >= 1500.0:
                    self._adaptive_mode = "conn_mgr_congested"
                    return (240.0, "conn_mgr_congested")
            except (AttributeError, TypeError):
                pass

        if self._battery is None:
            return (90.0, "bootstrap_battery")

        if force_connect and self._connection_error_classification in {
            "scanner_unavailable",
            "slot_timeout",
            "connect_error",
        }:
            return (180.0, "recovery_after_connect_failure")

        base = float(self.battery_poll_interval_min * 60)
        jitter = float(random.randint(0, BATTERY_POLL_JITTER_SECONDS))
        return (base + jitter, "normal_poll")

    async def _async_operation_worker(self) -> None:
        while True:
            _, _, op = await self._op_queue.get()
            try:
                attempt = 0
                while True:
                    try:
                        if op.name in {"start_alarm", "stop_alarm"}:
                            self._last_alarm_operation_ts = time.monotonic()
                        result = await op.action()
                        if not op.future.done():
                            op.future.set_result(result)
                        break
                    except asyncio.CancelledError:
                        if not op.future.done():
                            op.future.cancel()
                        raise
                    except (BleakError, TimeoutError, OSError) as err:
                        attempt += 1
                        self._last_operation_error = f"{op.name}: {err}"
                        should_retry = (
                            attempt <= op.retries
                            and self._is_retryable_operation_error(err)
                        )
                        if should_retry:
                            _LOGGER.debug(
                                "设备 %s 操作 %s 失败，重试 %d/%d: %s",
                                self.address,
                                op.name,
                                attempt,
                                op.retries,
                                err,
                            )
                            await asyncio.sleep(op.retry_delay * (2 ** (attempt - 1)))
                            continue
                        if not op.future.done():
                            op.future.set_exception(err)
                        break
                    except Exception as err:  # noqa: BLE001
                        self._last_operation_error = f"{op.name}: {err}"
                        if not op.future.done():
                            op.future.set_exception(err)
                        break
            finally:
                self._op_queue.task_done()

    def _ble_device_callback(self) -> BLEDevice | None:
        return bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )

    async def _release_connection_slot(self) -> None:
        """Release global connection slot if acquired."""
        if self._conn_mgr is not None and self._conn_slot_acquired:
            await self._conn_mgr.release()
            self._conn_slot_acquired = False

    def _release_connection_slot_soon(self) -> None:
        """Release connection slot from non-async callback context.

        This is called from synchronous callbacks (like _on_disconnect),
        so we need to schedule the async release without blocking.
        """
        if self._conn_mgr is not None and self._conn_slot_acquired:
            self._conn_slot_acquired = False
            # Add error handling to prevent slot leakage on task creation failure
            try:
                task = self.hass.async_create_task(self._release_connection_slot())

                # Add completion callback to catch exceptions in task
                def _task_done(t: asyncio.Task) -> None:
                    try:
                        t.exception()
                    except Exception as err:
                        _LOGGER.error("Error in slot release task: %s", err)

                task.add_done_callback(_task_done)
            except Exception as err:
                _LOGGER.error("Failed to schedule slot release: %s", err)

    def _apply_connect_backoff(self, *, max_backoff: int) -> int:
        """Increase failure count and apply exponential cooldown."""
        self._connect_fail_count = min(
            self._connect_fail_count + 1, MAX_CONNECT_FAIL_COUNT
        )
        backoff = min(max_backoff, (2**self._connect_fail_count))
        self._cooldown_until_ts = time.time() + backoff
        return backoff

    def _set_connection_state(self, state: str) -> None:
        if self._connection_state != state:
            self._connection_state = state

    def _on_disconnect(self, _client) -> None:
        """Handle disconnect callback from bleak.

        Note: This is a synchronous callback from bleak, running on a background thread.
        All cleanup operations must be non-blocking.
        """
        try:
            self._connected = False
            self._set_connection_state("degraded")

            # ====== 对齐 HA IQS log-when-unavailable：记录不可用日志（仅一次） ======
            if not self._unavailability_logged:
                _LOGGER.info("Device %s unavailable", self.name)
                self._unavailability_logged = True

            # ====== 清除特征缓存（断开连接后缓存失效） ======
            # 清理特征缓存（如果失败，记录错误但继续清理）
            try:
                self._cached_chars.clear()
            except Exception as err:
                _LOGGER.error("Error clearing characteristic cache: %s", err)
        except Exception as err:
            _LOGGER.error("Error in disconnect callback: %s", err)
        finally:
            # ====== 断开：归还全局连接槽位 ======
            # 确保资源释放一定会执行
            self._release_connection_slot_soon()
            # ====== 结束 ======
            self._client = None
            self._alert_level_handle = None
            self._battery_level_handle = None
            self._async_dispatch_update()

        if self.auto_reconnect and self.maintain_connection:
            self._ensure_connect_task()

    async def async_ensure_connected(self, *, connect_purpose: str = "general") -> bool:
        """Ensure BLE connection is established and ready for GATT operations.

        Returns:
            True if connection is ready for GATT operations, False otherwise.
        """
        async with self._connect_lock:
            # ====== 连接退避：避免多设备同时冲连接 ======
            now_ts = time.time()
            if now_ts < self._cooldown_until_ts:
                self._set_connection_state("backoff")
                return False
            if self._connected and self._client is not None:
                self._set_connection_state("ready")
                return True

            self._set_connection_state("connecting")

            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if ble_device is None:
                self._last_error = "No connectable BLEDevice available (out of range or no connectable scanner)."
                self._connection_error_classification = "scanner_unavailable"
                self._connection_error_type = "device_not_connectable"
                self._connected = False
                self._client = None
                self._set_connection_state("scanning")

                # ====== 主动断开：归还全局连接槽位 ======
                await self._release_connection_slot()
                # ====== 结束 ======
                self._async_dispatch_update()
                return False

            # ====== 获取全局连接槽位（跨设备并发控制） ======
            if self._conn_mgr is not None and not self._conn_slot_acquired:
                slot_timeout = self._compute_slot_acquire_timeout(
                    connect_purpose=connect_purpose
                )
                acq = await self._conn_mgr.acquire(timeout=slot_timeout)
                if not acq.acquired:
                    backoff = self._apply_connect_backoff(
                        max_backoff=MAX_CONNECT_BACKOFF_SECONDS // 2
                    )
                    self._last_error = f"等待连接槽位中({acq.reason}, timeout={slot_timeout:.1f}s); {backoff}s 后重试"
                    self._connection_error_classification = "slot_timeout"
                    self._connection_error_type = f"acquire_failed:{acq.reason}"
                    self._connected = False
                    self._client = None
                    self._set_connection_state("backoff")
                    self._async_dispatch_update()
                    return False
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
            except (
                BleakOutOfConnectionSlotsError,
                BleakNotFoundError,
                BleakAbortedError,
                BleakConnectionError,
            ) as err:
                # ====== 连接失败：归还全局连接槽位 + 退避 ======
                await self._release_connection_slot()
                backoff = self._apply_connect_backoff(
                    max_backoff=MAX_CONNECT_BACKOFF_SECONDS
                )
                self._last_error = f"连接失败: {err}; {backoff}s 后重试"
                self._connection_error_classification = "connect_error"
                self._connection_error_type = type(err).__name__
                self._connected = False
                self._client = None
                self._set_connection_state("backoff")
                self._async_dispatch_update()
                return False

            self._set_connection_state("discovering")
            try:
                # 访问 services 属性触发服务发现（bleak 的 services 是 property）
                _ = client.services
            except BleakError as err:
                await self._release_connection_slot()
                backoff = self._apply_connect_backoff(
                    max_backoff=MAX_CONNECT_BACKOFF_SECONDS
                )
                self._last_error = f"服务发现失败: {err}; {backoff}s 后重试"
                self._connection_error_classification = "service_discovery_error"
                self._connection_error_type = "BleakError"
                self._connected = False
                self._client = None
                self._set_connection_state("degraded")
                self._async_dispatch_update()
                try:
                    await client.disconnect()
                except BleakError:
                    pass
                return False

            self._client = client
            self._connected = True
            self._last_error = None
            self._connection_error_classification = None
            self._connection_error_type = None
            self._connect_fail_count = 0
            self._cooldown_until_ts = 0.0

            # ====== 对齐 HA IQS log-when-unavailable：记录恢复日志（仅一次） ======
            if self._unavailability_logged:
                _LOGGER.info("Device %s recovered", self.name)
                self._unavailability_logged = False

            init_ok = await self._async_post_connect_setup()
            self._set_connection_state("ready" if init_ok else "degraded")
            self._async_dispatch_update()
            return True

    async def async_disconnect(self) -> None:
        async with self._connect_lock:
            if self._client is None:
                self._connected = False
                self._async_dispatch_update()
                return
            try:
                try:
                    await self._client.stop_notify(UUID_NOTIFY_FFE1)
                except BleakError:
                    # stop_notify may fail if already disconnected
                    pass
                await self._client.disconnect()
            finally:
                self._client = None
                self._connected = False
                self._alert_level_handle = None
                self._battery_level_handle = None
                self._set_connection_state("idle")
                self._async_dispatch_update()

    async def _async_post_connect_setup(self) -> bool:
        """Run post-connection initialization pipeline."""
        self._resolve_gatt_handles()

        notifications_ok = await self._async_enable_notifications()
        if not notifications_ok:
            self._connection_error_classification = "notify_error"
            self._connection_error_type = "start_notify_failed"

        # 对齐 Android 流程：连接稳定后立即读取一次电量
        await self._async_read_battery_impl(force_connect=False)

        # 最佳努力同步断开报警策略，失败不影响连接可用性
        try:
            await self._async_write_bytes(
                UUID_WRITE_FFE2,
                bytes([0x01 if self.alarm_on_disconnect else 0x00]),
                prefer_response=True,
                connect_purpose="policy_sync",
            )
        except (BleakError, TimeoutError, OSError) as err:
            self._last_error = f"同步断开报警策略失败: {err}"
            _LOGGER.debug("设备 %s 策略同步失败: %s", self.address, err)

        return notifications_ok

    async def _async_enable_notifications(self) -> bool:
        client = self._client
        if client is None:
            return False

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
            return True
        except BleakError as err:
            self._last_error = f"开启通知(FFE1)失败: {err}"
            self._async_dispatch_update()
            return False

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
        """解析特征handle，使用缓存提高性能。

        集成自device/gatt_operations.py的特征缓存机制。
        """
        client = self._client
        if client is None:
            return None

        services = getattr(client, "services", None)
        if services is None:
            return None

        cu = self._normalize_uuid(char_uuid)

        # ====== 特征缓存：先检查缓存 ======
        if cu in self._cached_chars:
            ch = self._cached_chars[cu]
            handle = getattr(ch, "handle", None)
            if handle is not None:
                return handle
        psu = (
            self._normalize_uuid(preferred_service_uuid)
            if preferred_service_uuid
            else None
        )

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
                except (AttributeError, TypeError, ValueError):
                    handles.append((svc_uuid, None))
            _LOGGER.warning(
                "Multiple characteristics for UUID %s; selecting the first by handle. Candidates=%s",
                char_uuid,
                handles,
            )

        try:
            ch = matches[0][1]
            handle = int(getattr(ch, "handle"))

            # ====== 缓存特征对象（集成自device/gatt_operations.py） ======
            self._cached_chars[cu] = ch

            return handle
        except (AttributeError, TypeError, ValueError):
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
        async def _action() -> None:
            char = (
                self._alert_level_handle
                if self._alert_level_handle is not None
                else UUID_ALERT_LEVEL_2A06
            )
            await self._async_write_bytes(
                char,
                bytes([0x01]),
                prefer_response=False,
                connect_purpose="interactive_alarm",
            )

        await self._async_enqueue_operation(
            name="start_alarm",
            action=_action,
            priority=self._op_priority_alarm,
            retries=1,
            retry_delay=0.6,
        )

    async def async_stop_alarm(self) -> None:
        async def _action() -> None:
            char = (
                self._alert_level_handle
                if self._alert_level_handle is not None
                else UUID_ALERT_LEVEL_2A06
            )
            await self._async_write_bytes(
                char,
                bytes([0x00]),
                prefer_response=False,
                connect_purpose="interactive_alarm",
            )

        await self._async_enqueue_operation(
            name="stop_alarm",
            action=_action,
            priority=self._op_priority_alarm,
            retries=1,
            retry_delay=0.6,
        )

    async def async_set_disconnect_alarm_policy(
        self, enabled: bool, force_connect: bool
    ) -> None:
        async def _action() -> None:
            value = bytes([0x01 if enabled else 0x00])
            if self._client is None and force_connect:
                await self.async_ensure_connected(connect_purpose="policy_sync")
                # If user does not want to maintain connection, disconnect afterwards
                if not self.maintain_connection:
                    try:
                        await self._async_write_bytes(
                            UUID_WRITE_FFE2,
                            value,
                            prefer_response=True,
                            connect_purpose="policy_sync",
                        )
                    finally:
                        await self.async_disconnect()
                    return
            await self._async_write_bytes(
                UUID_WRITE_FFE2,
                value,
                prefer_response=True,
                connect_purpose="policy_sync",
            )

        await self._async_enqueue_operation(
            name="sync_disconnect_policy",
            action=_action,
            priority=self._op_priority_policy,
            retries=1,
            retry_delay=0.8,
        )

    async def _async_gatt_operation_with_uuid_fallback(
        self,
        client: BleakClient,
        char_specifier: str | int,
        operation: str,
        preferred_service_uuid: str | None = None,
        require_write: bool = False,
        write_data: bytes | None = None,
        response: bool | None = None,
    ) -> Any:
        """统一的GATT操作函数，处理同UUID多特征的降级逻辑。

        Args:
            client: Bleak客户端实例
            char_specifier: 特征标识符（UUID字符串或handle整数）
            operation: 操作类型（'read' 或 'write'）
            preferred_service_uuid: 优先匹配的服务UUID（可选）
            require_write: 是否要求可写特征（用于handle解析）
            write_data: 写入数据（仅write操作需要）
            response: 是否要求响应（仅write操作需要）

        Returns:
            read操作返回读取的数据，write操作无返回值

        Raises:
            BleakError: 操作失败且无法降级时抛出
        """
        if operation not in ("read", "write"):
            raise ValueError(f"不支持的GATT操作类型: {operation}")

        def _resolve_handle_for_uuid(uuid_str: str) -> int | None:
            """解析UUID对应的handle"""
            return self._resolve_char_handle(
                uuid_str,
                preferred_service_uuid=preferred_service_uuid,
                require_write=require_write,
            )

        async def _do_operation(specifier: str | int) -> Any:
            """执行实际的GATT操作"""
            if operation == "read":
                return await client.read_gatt_char(specifier)
            else:  # write
                if write_data is None:
                    raise ValueError("write操作需要提供write_data")
                return await client.write_gatt_char(
                    specifier, write_data, response=response
                )  # type: ignore[arg-type]

        try:
            return await _do_operation(char_specifier)
        except BleakError as err:
            if isinstance(
                char_specifier, str
            ) and "Multiple Characteristics with this UUID" in str(err):
                # 访问 services 属性确保服务发现完成（bleak 的 services 是 property）
                _ = client.services
                # 刷新 handle 缓存
                self._cached_chars.clear()

                handle = _resolve_handle_for_uuid(char_specifier)
                if handle is not None:
                    _LOGGER.debug(
                        "UUID %s 触发多特征错误，降级使用 handle %s",
                        char_specifier,
                        handle,
                    )
                    return await _do_operation(handle)
            raise

    async def async_read_battery(self, force_connect: bool) -> None:
        # 避免后台轮询重复堆积读电量任务
        if self._battery_read_lock.locked() and not force_connect:
            return

        async with self._battery_read_lock:
            await self._async_enqueue_operation(
                name="read_battery",
                action=lambda: self._async_read_battery_impl(
                    force_connect=force_connect
                ),
                priority=self._op_priority_battery,
                retries=1,
                retry_delay=1.2,
            )

    async def _async_read_battery_impl(self, force_connect: bool) -> None:
        if self._client is None:
            if not force_connect:
                # 节流日志：只在首次或长时间未读取时记录
                if self._last_battery_read is None:
                    _LOGGER.debug(
                        "设备 %s 电量尚未读取，但当前未连接且未启用强制连接（将在首次读取时自动尝试）",
                        self.address,
                    )
                return
            connected = await self.async_ensure_connected(
                connect_purpose="background_battery"
            )
            if not connected or self._client is None:
                _LOGGER.warning(
                    "设备 %s 无法建立连接以读取电量: %s",
                    self.address,
                    self._last_error or "未知错误",
                )
                return

        async with self._gatt_lock:
            client = self._client
            if client is None:
                return
            try:
                char = (
                    self._battery_level_handle
                    if self._battery_level_handle is not None
                    else UUID_BATTERY_LEVEL_2A19
                )
                data = await self._async_gatt_operation_with_uuid_fallback(
                    client=client,
                    char_specifier=char,
                    operation="read",
                    preferred_service_uuid=_UUID_SERVICE_BATTERY_180F,
                    require_write=False,
                )
                if data and len(data) >= 1:
                    level = int(data[0])
                    level = max(0, min(100, level))
                    self._battery = level
                    self._last_battery_read = datetime.now(timezone.utc)
                    _LOGGER.debug("设备 %s 电量读取成功: %d%%", self.address, level)
                    self._async_dispatch_update()
            except BleakError as err:
                self._last_error = f"读取电量失败: {err}"
                self._async_dispatch_update()
            except (TimeoutError, OSError, asyncio.CancelledError) as err:
                self._last_error = f"读取电量失败（超时或系统错误）: {err}"
                self._async_dispatch_update()

    async def _async_write_bytes(
        self,
        uuid: str | int,
        data: bytes,
        prefer_response: bool,
        connect_purpose: str = "general",
    ) -> None:
        if self._client is None:
            connected = await self.async_ensure_connected(
                connect_purpose=connect_purpose
            )
            if not connected or self._client is None:
                error_detail = self._last_error or "未知错误"
                raise BleakError(
                    f"无法为设备 {self.name}({self.address}) 建立连接用于写入 {uuid}: {error_detail}"
                )

        async with self._gatt_lock:
            client = self._client
            if client is None:
                error_detail = self._last_error or "未知错误"
                raise BleakError(
                    f"无法为设备 {self.name}({self.address}) 获取 BLE 客户端用于写入 {uuid}: {error_detail}"
                )

            # 确定2A06（报警）的优先服务UUID
            def _get_preferred_service(u: str) -> str | None:
                if u.lower() == UUID_ALERT_LEVEL_2A06.lower():
                    return _UUID_SERVICE_IMMEDIATE_ALERT_1802
                return None

            # Try preferred response mode first, then fallback
            response_modes = [prefer_response, not prefer_response]

            for i, response_mode in enumerate(response_modes):
                try:
                    await self._async_gatt_operation_with_uuid_fallback(
                        client=client,
                        char_specifier=uuid,
                        operation="write",
                        preferred_service_uuid=_get_preferred_service(uuid)
                        if isinstance(uuid, str)
                        else None,
                        require_write=True,
                        write_data=data,
                        response=response_mode,
                    )
                    return
                except (BleakError, TimeoutError, OSError) as err:
                    if i < len(response_modes) - 1:
                        continue
                    self._last_error = f"写入 {uuid} 失败: {err}"
                    self._async_dispatch_update()
                    raise

    async def _async_battery_loop(self) -> None:
        # 启动后立即尝试一次读取，避免首次电量长时间 unknown
        await asyncio.sleep(random.uniform(0.5, 3.0))
        while True:
            try:
                # 首次读取或电量为 None 时，强制建立连接
                force = (self._battery is None) or (not self.maintain_connection)

                if self._should_defer_battery_poll():
                    self._battery_defer_count += 1
                    self._last_battery_sleep_seconds = 15.0
                    self._last_battery_sleep_reason = "defer_for_foreground"
                    await asyncio.sleep(15.0)
                    continue

                await self.async_read_battery(force_connect=force)
                next_sleep, reason = self._compute_next_battery_sleep_seconds(
                    force_connect=force
                )
                self._last_battery_sleep_seconds = next_sleep
                self._last_battery_sleep_reason = reason
                await asyncio.sleep(next_sleep)
                # ====== 结束 ======
            except asyncio.CancelledError:
                # 任务被取消，清理资源后重新抛出
                _LOGGER.debug("Battery loop cancelled for %s", self.address)
                raise
            except (BleakError, TimeoutError, OSError) as err:
                self._last_error = f"电量轮询异常: {err}"
                self._async_dispatch_update()
