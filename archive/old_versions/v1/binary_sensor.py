from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)

from .const import DOMAIN
from .device import AntiLossTagDevice


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    device: AntiLossTagDevice = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AntiLossTagInRangeBinarySensor(device),
            AntiLossTagConnectedBinarySensor(device),
        ],
        update_before_add=False,
    )


class _AntiLossTagBinaryBase(BinarySensorEntity):
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
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._dev.address)},
            name=self._dev.name,
            manufacturer="未知",
            model="BLE 防丢标签",
        )


class AntiLossTagInRangeBinarySensor(_AntiLossTagBinaryBase):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, device: AntiLossTagDevice) -> None:
        super().__init__(device)
        self._attr_name = f"{device.name} 在范围内"
        self._attr_unique_id = f"{device.address}_in_range"

    @property
    def is_on(self) -> bool:
        return self._dev.available


class AntiLossTagConnectedBinarySensor(_AntiLossTagBinaryBase):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, device: AntiLossTagDevice) -> None:
        super().__init__(device)
        self._attr_name = f"{device.name} 已连接"
        self._attr_unique_id = f"{device.address}_connected"

    @property
    def is_on(self) -> bool:
        return self._dev.connected
