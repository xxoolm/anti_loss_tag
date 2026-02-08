from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory

from .const import DOMAIN
from .device import AntiLossTagDevice


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    device: AntiLossTagDevice = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AntiLossTagStartAlarmButton(device),
            AntiLossTagStopAlarmButton(device),
        ],
        update_before_add=False,
    )


class _AntiLossTagButtonBase(ButtonEntity):
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
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._dev.address)},
            name=self._dev.name,
            manufacturer="未知",
            model="BLE 防丢标签",
        )

    @property
    def available(self) -> bool:
        # We allow pressing even if not connected; device will connect as needed
        return self._dev.available or self._dev.connected


class AntiLossTagStartAlarmButton(_AntiLossTagButtonBase):
    def __init__(self, device: AntiLossTagDevice) -> None:
        super().__init__(device)
        self._attr_name = f"{device.name} 开始报警"
        self._attr_unique_id = f"{device.address}_start_alarm"

    async def async_press(self) -> None:
        await self._dev.async_start_alarm()


class AntiLossTagStopAlarmButton(_AntiLossTagButtonBase):
    def __init__(self, device: AntiLossTagDevice) -> None:
        super().__init__(device)
        self._attr_name = f"{device.name} 停止报警"
        self._attr_unique_id = f"{device.address}_stop_alarm"

    async def async_press(self) -> None:
        await self._dev.async_stop_alarm()
