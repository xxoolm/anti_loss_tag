# SPDX-License-Identifier: MIT
# Copyright (c) 2025-2026 MMMM
# See LICENSE file for details
from __future__ import annotations

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .device import AntiLossTagDevice, ButtonEvent
from .entity_mixin import AntiLossTagEntityMixin


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    device: AntiLossTagDevice = entry.runtime_data
    async_add_entities([AntiLossTagButtonEventEntity(device)], update_before_add=False)


class AntiLossTagButtonEventEntity(AntiLossTagEntityMixin, EventEntity):
    _attr_has_entity_name = True
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = ["press"]

    def __init__(self, device: AntiLossTagDevice) -> None:
        self._dev = device
        self._unsub_btn = None
        self._attr_name = "Button"
        self._attr_unique_id = f"{device.address}_button_event"

    async def async_added_to_hass(self) -> None:
        self._unsub_btn = self._dev.async_add_button_listener(self._async_on_button)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_btn is not None:
            self._unsub_btn()
            self._unsub_btn = None

    @callback
    def _async_on_button(self, event: ButtonEvent) -> None:
        self._trigger_event(
            "press", {"entity_id": self.entity_id, "raw_hex": event.raw.hex()}
        )
        self.async_write_ha_state()
