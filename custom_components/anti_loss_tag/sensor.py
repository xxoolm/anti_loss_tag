from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    PERCENTAGE,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)

from .device import AntiLossTagDevice
from .entity_mixin import AntiLossTagEntityMixin


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    device: AntiLossTagDevice = entry.runtime_data
    async_add_entities(
        [
            AntiLossTagRssiSensor(device, entry),
            AntiLossTagBatterySensor(device, entry),
        ],
        update_before_add=False,
    )


class _AntiLossTagSensorBase(AntiLossTagEntityMixin, SensorEntity):
    """Base class for AntiLossTag sensors."""

    def __init__(self, device: AntiLossTagDevice, entry: ConfigEntry) -> None:
        self._dev = device
        self._entry = entry
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        self._unsub = self._dev.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None


class AntiLossTagRssiSensor(_AntiLossTagSensorBase):
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device: AntiLossTagDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry)
        self._attr_name = "Signal Strength"
        self._attr_unique_id = f"{device.address}_rssi"

    @property
    def native_value(self) -> int | None:
        return self._dev.rssi


class AntiLossTagBatterySensor(_AntiLossTagSensorBase):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device: AntiLossTagDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry)
        self._attr_name = "Battery"
        self._attr_unique_id = f"{device.address}_battery"

    @property
    def native_value(self) -> int | None:
        return self._dev.battery

    @property
    def available(self) -> bool:
        # Battery is only known after at least one successful read
        return self._dev.battery is not None
