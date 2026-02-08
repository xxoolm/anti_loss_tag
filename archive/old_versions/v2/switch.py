from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory

from .const import DOMAIN
from .device import AntiLossTagDevice


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    device: AntiLossTagDevice = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AntiLossTagDisconnectAlarmPolicySwitch(device, entry)], update_before_add=False)


class AntiLossTagDisconnectAlarmPolicySwitch(SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, device: AntiLossTagDevice, entry: ConfigEntry) -> None:
        self._dev = device
        self._entry = entry
        self._unsub = None
        self._attr_name = f"{device.name} 断连报警"
        self._attr_unique_id = f"{device.address}_alarm_on_disconnect"

    async def async_added_to_hass(self) -> None:
        self._unsub = self._dev.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._dev.address)},
            name=self._dev.name,
            manufacturer="未知",
            model="BLE 防丢标签",
        )

    @property
    def is_on(self) -> bool:
        return self._dev.alarm_on_disconnect

    async def async_turn_on(self, **kwargs) -> None:
        # Persist option and sync to device
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={**self._entry.options, "alarm_on_disconnect": True},
        )
        await self._dev.async_set_disconnect_alarm_policy(True, force_connect=not self._dev.maintain_connection)

    async def async_turn_off(self, **kwargs) -> None:
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={**self._entry.options, "alarm_on_disconnect": False},
        )
        await self._dev.async_set_disconnect_alarm_policy(False, force_connect=not self._dev.maintain_connection)
