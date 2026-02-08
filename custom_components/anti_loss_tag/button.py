# SPDX-License-Identifier: MIT
# Copyright (c) 2025-2026 MMMM
# See LICENSE file for details
from __future__ import annotations

import logging

from bleak.exc import BleakError
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .device import AntiLossTagDevice
from .entity_mixin import AntiLossTagEntityMixin

_LOGGER = logging.getLogger(__name__)


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
    _attr_parallel_updates = 1

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
        self._attr_name = "开始报警"
        self._attr_unique_id = f"{device.address}_start_alarm"

    async def async_press(self) -> None:
        try:
            await self._dev.async_start_alarm()
        except BleakError as err:
            error_classification = (
                self._dev.connection_error_classification or "unknown"
            )
            error_type = self._dev.connection_error_type or "unknown"
            _LOGGER.error(
                "开始报警失败: %s (错误类型: %s/%s)",
                err,
                error_classification,
                error_type,
            )
            raise HomeAssistantError(f"开始报警失败: {err}") from err


class AntiLossTagStopAlarmButton(_AntiLossTagButtonBase):
    def __init__(self, device: AntiLossTagDevice) -> None:
        super().__init__(device)
        self._attr_name = "停止报警"
        self._attr_unique_id = f"{device.address}_stop_alarm"

    async def async_press(self) -> None:
        try:
            await self._dev.async_stop_alarm()
        except BleakError as err:
            error_classification = (
                self._dev.connection_error_classification or "unknown"
            )
            error_type = self._dev.connection_error_type or "unknown"
            _LOGGER.error(
                "停止报警失败: %s (错误类型: %s/%s)",
                err,
                error_classification,
                error_type,
            )
            raise HomeAssistantError(f"停止报警失败: {err}") from err
