from __future__ import annotations

import asyncio
from typing import Optional

from bleak import BleakClient
from bleak.exc import BleakError

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    CHAR_ALERT_LEVEL_2A06,
    CHAR_WRITE_FFE2,
    CHAR_BATTERY_2A19,
)


class BleTagBle:
    """
    统一封装 BLE GATT 操作，并发串行化（一个设备同一时间只允许一个 connect/read/write）。
    """

    def __init__(self, hass: HomeAssistant, address: str):
        self._hass = hass
        self._address = address
        self._lock = asyncio.Lock()

    async def _client(self) -> BleakClient:
        dev = bluetooth.async_ble_device_from_address(self._hass, self._address)
        if dev is None:
            # 允许 bleak 用地址直连（某些环境下 HA 蓝牙设备对象可能暂时拿不到）
            return BleakClient(self._address, timeout=20)
        return BleakClient(dev, timeout=20)

    async def write_alert_level(self, on: bool) -> None:
        async with self._lock:
            client = await self._client()
            async with client:
                await client.write_gatt_char(CHAR_ALERT_LEVEL_2A06, bytes([1 if on else 0]), response=True)

    async def write_disconnect_alarm(self, enabled: bool) -> None:
        async with self._lock:
            client = await self._client()
            async with client:
                await client.write_gatt_char(CHAR_WRITE_FFE2, bytes([1 if enabled else 0]), response=True)

    async def read_battery(self) -> Optional[int]:
        async with self._lock:
            client = await self._client()
            async with client:
                data = await client.read_gatt_char(CHAR_BATTERY_2A19)
                if data and len(data) > 0:
                    v = int(data[0])
                    if 0 <= v <= 100:
                        return v
                return None
