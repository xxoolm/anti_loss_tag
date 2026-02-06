from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .ble import BleTagBle
from .const import (
    DOMAIN,
    CONF_ADDRESS,
    CONF_NAME,
    SERVICE_UUID_FFE0,
    DEFAULT_ONLINE_TIMEOUT_SECONDS,
    DEFAULT_BATTERY_CACHE_SECONDS,
)


@dataclass
class BleTagData:
    address: str
    name: str
    rssi: int | None = None
    last_seen: str | None = None  # ISO string
    online: bool = False
    battery: int | None = None
    disconnect_alarm: bool = False
    battery_last_read_ts: float | None = None


class BleTagCoordinator(DataUpdateCoordinator[BleTagData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self.address = entry.data[CONF_ADDRESS]
        self.name = entry.data.get(CONF_NAME, "BLE 标签")

        import logging
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=f"{DOMAIN}-{self.address}",
            update_interval=None,
        )


        self.ble = BleTagBle(hass, self.address)
        self._unsub_adv = None

        self.data = BleTagData(
            address=self.address,
            name=self.name,
            disconnect_alarm=False,
        )

    async def async_start(self) -> None:
        matcher = BluetoothCallbackMatcher(address=self.address, service_uuid=SERVICE_UUID_FFE0)

        self._unsub_adv = bluetooth.async_register_callback(
            self.hass,
            self._adv_callback,
            matcher,
            BluetoothScanningMode.ACTIVE,
        )

        # 初始刷新一次（主要用于 online 状态）
        self.async_set_updated_data(self._recalc_online(self.data))

    async def async_stop(self) -> None:
        if self._unsub_adv is not None:
            self._unsub_adv()
            self._unsub_adv = None

    @callback
    def _adv_callback(self, service_info: BluetoothServiceInfoBleak, change) -> None:
        now = dt_util.utcnow()
        d = self.data
        d.rssi = service_info.rssi
        d.last_seen = now.isoformat()
        self.async_set_updated_data(self._recalc_online(d))



    def _recalc_online(self, d: BleTagData) -> BleTagData:
        timeout = timedelta(seconds=DEFAULT_ONLINE_TIMEOUT_SECONDS)
        if d.last_seen:
            try:
                last = dt_util.parse_datetime(d.last_seen)
            except Exception:
                last = None
            if last:
                d.online = (dt_util.utcnow() - last) <= timeout
            else:
                d.online = False
        else:
            d.online = False
        return d

    async def async_refresh_battery(self, force: bool = False) -> None:
        """
        电量读取需要连接 GATT，比较“重”，这里做缓存。
        """
        now_ts = dt_util.utcnow().timestamp()
        d = self.data

        if (not force) and d.battery_last_read_ts is not None:
            if (now_ts - d.battery_last_read_ts) < DEFAULT_BATTERY_CACHE_SECONDS:
                return

        battery = await self.ble.read_battery()
        if battery is not None:
            d.battery = battery
            d.battery_last_read_ts = now_ts
            self.async_set_updated_data(self._recalc_online(d))

    async def async_set_disconnect_alarm(self, enabled: bool) -> None:
        await self.ble.write_disconnect_alarm(enabled)
        d = self.data
        d.disconnect_alarm = enabled
        self.async_set_updated_data(self._recalc_online(d))

    async def async_ring(self, seconds: int = 2) -> None:
        await self.ble.write_alert_level(True)
        await self.hass.async_add_executor_job(lambda: None)
        await self.hass.async_add_executor_job(lambda: None)

        # 用 HA 的 async sleep（避免阻塞）
        import asyncio
        await asyncio.sleep(max(1, int(seconds)))

        await self.ble.write_alert_level(False)
