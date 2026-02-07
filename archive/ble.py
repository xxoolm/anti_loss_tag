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
    统一封装 BLE GATT 操作，并发串行化（一个设备同一时间只允许一个 connect/read/write）。

    使用最佳实践：
    - BleakClientWithServiceCache：缓存服务发现结果
    - establish_connection：自动重试机制
    - disconnected_callback：处理意外断开
    """

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        """初始化 BLE 操作封装。

        Args:
            hass: Home Assistant 实例
            address: BLE 设备地址
        """
        self._hass = hass
        self._address = address
        self._lock = asyncio.Lock()
        self._disconnected = False

    def _on_disconnect(self, client: BleakClientWithServiceCache) -> None:
        """处理意外断开连接回调。

        Args:
            client: 断开的客户端实例
        """
        self._disconnected = True
        _LOGGER.warning("Device %s disconnected unexpectedly", self._address)

    async def _get_device(self) -> BLEDevice:
        """获取 BLE 设备对象。

        Returns:
            BLE 设备对象

        Raises:
            BleakConnectionError: 如果设备未找到
        """
        dev = bluetooth.async_ble_device_from_address(self._hass, self._address)
        if dev is None:
            raise BleakConnectionError(f"Device {self._address} not found")
        return dev

    async def write_alert_level(self, on: bool) -> None:
        """写入报警级别特征。

        Args:
            on: True 为开启报警，False 为关闭

        Raises:
            BleakConnectionError: 连接失败
            BleakError: 写入失败
        """
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
        """写入断连报警特征。

        Args:
            enabled: True 为启用断连报警，False 为禁用

        Raises:
            BleakConnectionError: 连接失败
            BleakError: 写入失败
        """
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
        """读取电池电量。

        Returns:
            电池电量百分比（0-100），如果读取失败则返回 None

        Raises:
            BleakConnectionError: 连接失败
            BleakError: 读取失败
        """
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
