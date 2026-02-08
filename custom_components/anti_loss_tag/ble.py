# SPDX-License-Identifier: MIT
"""弃用的 BLE 操作封装模块。

此模块已被 device.py.AntiLossTagDevice 完全替代。
保留此文件仅用于向后兼容。

**请勿在新代码中使用此模块！**

迁移指南：
- BleTagBle → device.AntiLossTagDevice
- 详见 archived/DEPRECATED.md

弃用时间: 2025-02-08
"""

from __future__ import annotations

import asyncio
import logging
from typing import Final

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    BleakConnectionError,
    establish_connection,
)

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    CHAR_ALERT_LEVEL_2A06,
    CHAR_WRITE_FFE2,
    CHAR_BATTERY_2A19,
)

_LOGGER = logging.getLogger(__name__)
DEFAULT_BLEAK_TIMEOUT: Final = 20.0


class BleTagBle:
    """
    [已弃用] 统一封装 BLE GATT 操作。

    **请使用 device.py.AntiLossTagDevice 替代**

    此类已被完全替代，保留仅用于向后兼容。
    所有功能已整合到 AntiLossTagDevice 中。
    """

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        """[已弃用] 初始化 BLE 操作封装。

        请使用 device.AntiLossTagDevice 代替。
        """
        _LOGGER.warning(
            "BleTagBle is deprecated. Use device.AntiLossTagDevice instead."
        )
        self._hass = hass
        self._address = address
        self._lock = asyncio.Lock()
        self._disconnected = False

    def _on_disconnect(self, client: BleakClientWithServiceCache) -> None:
        """处理意外断开连接回调。"""
        self._disconnected = True
        _LOGGER.warning("Device %s disconnected unexpectedly", self._address)

    async def _get_device(self) -> BLEDevice:
        """获取 BLE 设备对象。"""
        dev = bluetooth.async_ble_device_from_address(self._hass, self._address)
        if dev is None:
            raise BleakConnectionError(f"Device {self._address} not found")
        return dev

    async def write_alert_level(self, on: bool) -> None:
        """[已弃用] 写入报警级别特征。

        请使用 AntiLossTagDevice.async_start_alarm() 或 async_stop_alarm()
        """
        _LOGGER.warning(
            "write_alert_level is deprecated. Use async_start_alarm/async_stop_alarm"
        )
        async with self._lock:
            dev = await self._get_device()
            try:
                async with await establish_connection(
                    BleakClientWithServiceCache,
                    dev,
                    self._address,
                    disconnected_callback=self._on_disconnect,
                    max_attempts=3,
                ) as client:
                    await client.write_gatt_char(
                        CHAR_ALERT_LEVEL_2A06, bytes([1 if on else 0]), response=True
                    )
                    _LOGGER.debug("Alert level set to %s for %s", on, self._address)
            except BleakError as err:
                _LOGGER.error(
                    "Failed to write alert level for %s: %s", self._address, err
                )
                raise

    async def write_disconnect_alarm(self, enabled: bool) -> None:
        """[已弃用] 写入断连报警特征。

        请使用 AntiLossTagDevice.async_set_disconnect_alarm_policy()
        """
        _LOGGER.warning(
            "write_disconnect_alarm is deprecated. Use async_set_disconnect_alarm_policy"
        )
        async with self._lock:
            dev = await self._get_device()
            try:
                async with await establish_connection(
                    BleakClientWithServiceCache,
                    dev,
                    self._address,
                    disconnected_callback=self._on_disconnect,
                    max_attempts=3,
                ) as client:
                    await client.write_gatt_char(
                        CHAR_WRITE_FFE2, bytes([1 if enabled else 0]), response=True
                    )
                    _LOGGER.debug(
                        "Disconnect alarm set to %s for %s", enabled, self._address
                    )
            except BleakError as err:
                _LOGGER.error(
                    "Failed to write disconnect alarm for %s: %s", self._address, err
                )
                raise

    async def read_battery(self) -> int | None:
        """[已弃用] 读取电池电量。

        请使用 AntiLossTagDevice.async_read_battery()
        """
        _LOGGER.warning("read_battery is deprecated. Use async_read_battery")
        async with self._lock:
            dev = await self._get_device()
            try:
                async with await establish_connection(
                    BleakClientWithServiceCache,
                    dev,
                    self._address,
                    disconnected_callback=self._on_disconnect,
                    max_attempts=3,
                ) as client:
                    data = await client.read_gatt_char(CHAR_BATTERY_2A19)
                    if data and len(data) > 0:
                        v = int(data[0])
                        if 0 <= v <= 100:
                            _LOGGER.debug(
                                "Battery level for %s: %s%%", self._address, v
                            )
                            return v
                        _LOGGER.warning(
                            "Invalid battery value for %s: %s", self._address, v
                        )
                    return None
            except BleakError as err:
                _LOGGER.error("Failed to read battery for %s: %s", self._address, err)
                raise
