from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.event import EventEntity, EventDeviceClass

from .const import DOMAIN
from .device import AntiLossTagDevice, ButtonEvent


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    device: AntiLossTagDevice = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AntiLossTagButtonEventEntity(device)], update_before_add=False)


class AntiLossTagButtonEventEntity(EventEntity):
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = ["press"]

    def __init__(self, device: AntiLossTagDevice) -> None:
        self._dev = device
        self._unsub_btn = None
        self._attr_name = f"{device.name} 按键"
        self._attr_unique_id = f"{device.address}_button_event"

    async def async_added_to_hass(self) -> None:
        self._unsub_btn = self._dev.async_add_button_listener(self._async_on_button)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_btn is not None:
            self._unsub_btn()
            self._unsub_btn = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._dev.address)},
            name=self._dev.name,
            manufacturer="未知",
            model="BLE 防丢标签",
        )

    @callback
    def _async_on_button(self, event: ButtonEvent) -> None:
        self._trigger_event("press", {"raw_hex": event.raw.hex()})
        self.async_write_ha_state()
