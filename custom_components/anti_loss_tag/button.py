# SPDX-License-Identifier: MIT
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
            AntiLossTagStartAlarmButton(device),
            AntiLossTagStopAlarmButton(device),
        ],
        update_before_add=False,
    )


class _AntiLossTagButtonBase(AntiLossTagEntityMixin, ButtonEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, device: AntiLossTagDevice) -> None:
        self._dev = device
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        self._unsub = self._dev.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    @property
    def available(self) -> bool:
        # Allow press even if not connected; device connects on demand
        return self._dev.available or self._dev.connected


class AntiLossTagStartAlarmButton(_AntiLossTagButtonBase):
    def __init__(self, device: AntiLossTagDevice) -> None:
        super().__init__(device)
        self._attr_name = "Start Alarm"
        self._attr_unique_id = f"{device.address}_start_alarm"

    async def async_press(self) -> None:
        await self._dev.async_start_alarm()


class AntiLossTagStopAlarmButton(_AntiLossTagButtonBase):
    def __init__(self, device: AntiLossTagDevice) -> None:
        super().__init__(device)
        self._attr_name = "Stop Alarm"
        self._attr_unique_id = f"{device.address}_stop_alarm"

    async def async_press(self) -> None:
        await self._dev.async_stop_alarm()
