# SPDX-License-Identifier: MIT
# Copyright (c) 2025-2026 MMMM
# See LICENSE file for details
"""弃用的协调器模块。

此模块已被 device.py.AntiLossTagDevice 完全替代。
保留此文件仅用于向后兼容。

**请勿在新代码中使用此模块！**

迁移指南：
- BleTagCoordinator → device.AntiLossTagDevice
- 详见 archived/DEPRECATED.md

弃用时间: 2025-02-08
"""

from __future__ import annotations

import asyncio
import logging
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

_LOGGER = logging.getLogger(__name__)


@dataclass
class BleTagData:
    """[已弃用] Coordinator 状态负载。"""

    address: str
    name: str
    rssi: int | None = None
    last_seen: str | None = None
    online: bool = False
    battery: int | None = None
    disconnect_alarm: bool = False
    battery_last_read_ts: float | None = None


class BleTagCoordinator(DataUpdateCoordinator[BleTagData]):
    """[已弃用] BLE 标签追踪协调器。

    **请使用 device.AntiLossTagDevice 替代**

    此类已被完全替代，保留仅用于向后兼容。
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """[已弃用] 初始化协调器。"""
        _LOGGER.warning(
            "BleTagCoordinator is deprecated. Use device.AntiLossTagDevice instead."
        )
        self.hass = hass
        self.entry = entry
        self.address = entry.data[CONF_ADDRESS]
        self.name = entry.data.get(CONF_NAME, "BLE 标签")

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
        """[已弃用] 启动广播监听器。"""
        _LOGGER.warning("BleTagCoordinator.async_start is deprecated")
        matcher = BluetoothCallbackMatcher(
            address=self.address, service_uuid=SERVICE_UUID_FFE0
        )

        self._unsub_adv = bluetooth.async_register_callback(
            self.hass,
            self._adv_callback,
            matcher,
            BluetoothScanningMode.ACTIVE,
        )

        self.async_set_updated_data(self._recalc_online(self.data))

    async def async_stop(self) -> None:
        """[已弃用] 停止广播监听器。"""
        _LOGGER.warning("BleTagCoordinator.async_stop is deprecated")
        if self._unsub_adv is not None:
            self._unsub_adv()
            self._unsub_adv = None

    @callback
    def _adv_callback(self, service_info: BluetoothServiceInfoBleak, change) -> None:
        """更新 RSSI 和 last_seen。"""
        now = dt_util.utcnow()
        d = self.data
        d.rssi = service_info.rssi
        d.last_seen = now.isoformat()
        self.async_set_updated_data(self._recalc_online(d))

    def _recalc_online(self, d: BleTagData) -> BleTagData:
        """重新计算在线状态。"""
        timeout = timedelta(seconds=DEFAULT_ONLINE_TIMEOUT_SECONDS)
        if d.last_seen:
            try:
                last = dt_util.parse_datetime(d.last_seen)
            except (ValueError, TypeError) as err:
                _LOGGER.debug("Failed to parse datetime: %s", err)
                last = None
            if last:
                d.online = (dt_util.utcnow() - last) <= timeout
            else:
                d.online = False
        else:
            d.online = False
        return d

    async def async_refresh_battery(self, force: bool = False) -> None:
        """[已弃用] 刷新电池电量。

        请使用 AntiLossTagDevice.async_read_battery()
        """
        _LOGGER.warning("async_refresh_battery is deprecated. Use async_read_battery")
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
        """[已弃用] 设置断连报警。

        请使用 AntiLossTagDevice.async_set_disconnect_alarm_policy()
        """
        _LOGGER.warning(
            "async_set_disconnect_alarm is deprecated. Use async_set_disconnect_alarm_policy"
        )
        await self.ble.write_disconnect_alarm(enabled)
        d = self.data
        d.disconnect_alarm = enabled
        self.async_set_updated_data(self._recalc_online(d))

    async def async_ring(self, seconds: int = 2) -> None:
        """[已弃用] 铃声报警。

        请使用 AntiLossTagDevice.async_start_alarm() 和 async_stop_alarm()
        """
        _LOGGER.warning(
            "async_ring is deprecated. Use async_start_alarm/async_stop_alarm"
        )
        await self.ble.write_alert_level(True)
        await asyncio.sleep(max(1, int(seconds)))
        await self.ble.write_alert_level(False)
