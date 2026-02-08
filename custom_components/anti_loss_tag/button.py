# SPDX-License-Identifier: MIT
# Copyright (c) 2025-2026 MMMM
# See LICENSE file for details
from __future__ import annotations

import asyncio
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

# 按钮操作重试配置
BUTTON_WRITE_MAX_RETRIES = 1  # 最大重试次数（总共尝试次数 = 1 + RETRY）
BUTTON_WRITE_RETRY_DELAY = 1.0  # 重试延迟（秒）


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
        last_err = None

        # 尝试执行操作（带重试）
        for attempt in range(BUTTON_WRITE_MAX_RETRIES + 1):
            try:
                await self._dev.async_start_alarm()
                return  # 成功，直接返回
            except BleakError as err:
                last_err = err
                error_type = getattr(self._dev, "_connection_error_type", "unknown")

                # 判断是否应该重试（仅在临时性错误时重试）
                should_retry = error_type in (
                    "scanner_unavailable",
                    "slot_timeout",
                    "connect_error",
                )

                if attempt < BUTTON_WRITE_MAX_RETRIES and should_retry:
                    _LOGGER.warning(
                        "开始报警失败（尝试 %d/%d），错误类型: %s，%s 秒后重试...",
                        attempt + 1,
                        BUTTON_WRITE_MAX_RETRIES + 1,
                        error_type,
                        BUTTON_WRITE_RETRY_DELAY,
                    )
                    await asyncio.sleep(BUTTON_WRITE_RETRY_DELAY)
                    continue
                else:
                    # 最后一次尝试或不应重试的错误
                    _LOGGER.error(
                        "按钮按下时写入失败: %s (错误类型: %s)", err, error_type
                    )
                    raise HomeAssistantError(f"开始报警失败: {err}") from err

        # 理论上不会到达这里（上面要么成功要么抛异常）
        if last_err:
            raise HomeAssistantError(f"开始报警失败: {last_err}") from last_err


class AntiLossTagStopAlarmButton(_AntiLossTagButtonBase):
    def __init__(self, device: AntiLossTagDevice) -> None:
        super().__init__(device)
        self._attr_name = "停止报警"
        self._attr_unique_id = f"{device.address}_stop_alarm"

    async def async_press(self) -> None:
        last_err = None

        # 尝试执行操作（带重试）
        for attempt in range(BUTTON_WRITE_MAX_RETRIES + 1):
            try:
                await self._dev.async_stop_alarm()
                return  # 成功，直接返回
            except BleakError as err:
                last_err = err
                error_type = getattr(self._dev, "_connection_error_type", "unknown")

                # 判断是否应该重试（仅在临时性错误时重试）
                should_retry = error_type in (
                    "scanner_unavailable",
                    "slot_timeout",
                    "connect_error",
                )

                if attempt < BUTTON_WRITE_MAX_RETRIES and should_retry:
                    _LOGGER.warning(
                        "停止报警失败（尝试 %d/%d），错误类型: %s，%s 秒后重试...",
                        attempt + 1,
                        BUTTON_WRITE_MAX_RETRIES + 1,
                        error_type,
                        BUTTON_WRITE_RETRY_DELAY,
                    )
                    await asyncio.sleep(BUTTON_WRITE_RETRY_DELAY)
                    continue
                else:
                    # 最后一次尝试或不应重试的错误
                    _LOGGER.error(
                        "按钮按下时写入失败: %s (错误类型: %s)", err, error_type
                    )
                    raise HomeAssistantError(f"停止报警失败: {err}") from err

        # 理论上不会到达这里（上面要么成功要么抛异常）
        if last_err:
            raise HomeAssistantError(f"停止报警失败: {last_err}") from last_err
