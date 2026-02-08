# SPDX-License-Identifier: MIT
# Copyright (c) 2025-2026 MMMM
# See LICENSE file for details
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .device import AntiLossTagDevice
from .entity_mixin import AntiLossTagEntityMixin


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    device: AntiLossTagDevice = entry.runtime_data
    async_add_entities(
        [
            AntiLossTagInRangeBinarySensor(device),
            AntiLossTagConnectedBinarySensor(device),
        ],
        update_before_add=False,
    )


class _AntiLossTagBinaryBase(AntiLossTagEntityMixin, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_parallel_updates = 0

    def __init__(self, device: AntiLossTagDevice) -> None:
        self._dev = device
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        self._unsub = self._dev.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None


class AntiLossTagInRangeBinarySensor(_AntiLossTagBinaryBase):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, device: AntiLossTagDevice) -> None:
        super().__init__(device)
        self._attr_name = "在线状态"
        self._attr_unique_id = f"{device.address}_in_range"

    @property
    def is_on(self) -> bool:
        return self._dev.available


class AntiLossTagConnectedBinarySensor(_AntiLossTagBinaryBase):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, device: AntiLossTagDevice) -> None:
        super().__init__(device)
        self._attr_name = "连接状态"
        self._attr_unique_id = f"{device.address}_connected"

    @property
    def is_on(self) -> bool:
        return self._dev.connected
