# SPDX-License-Identifier: MIT
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .device import AntiLossTagDevice
from .connection_manager import BleConnectionManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.EVENT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BLE Anti-Loss Tag from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # 全局 BLE 连接槽位管理器（限制同时保持的 GATT 连接数，提升多设备稳定性）
    hass.data[DOMAIN].setdefault("_conn_mgr", BleConnectionManager(max_connections=3))

    device = AntiLossTagDevice(hass=hass, entry=entry)
    entry.runtime_data = device

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    device.async_start()

    entry.async_on_unload(entry.add_update_listener(_async_update_entry))

    # Kick an initial connect attempt in background if user wants persistent connection
    hass.async_create_task(device.async_maybe_connect_initial())

    return True


async def _async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    device: AntiLossTagDevice = entry.runtime_data
    await device.async_apply_entry_options()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    device: AntiLossTagDevice = entry.runtime_data
    device.async_stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok
