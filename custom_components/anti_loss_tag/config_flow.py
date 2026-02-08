# SPDX-License-Identifier: MIT
# Copyright (c) 2025-2026 MMMM
# See LICENSE file for details
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_ADDRESS,
    CONF_ALARM_ON_DISCONNECT,
    CONF_AUTO_RECONNECT,
    CONF_BATTERY_POLL_INTERVAL_MIN,
    CONF_MAINTAIN_CONNECTION,
    CONF_NAME,
    DEFAULT_ALARM_ON_DISCONNECT,
    DEFAULT_AUTO_RECONNECT,
    DEFAULT_BATTERY_POLL_INTERVAL_MIN,
    DEFAULT_MAINTAIN_CONNECTION,
    DOMAIN,
)

from .utils.validation import is_valid_ble_address, is_valid_device_name


class AntiLossTagConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for BLE Anti-Loss Tag."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: BluetoothServiceInfoBleak | None = None
        self._address: str | None = None
        self._name: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle BLE discovery."""
        self._discovery = discovery_info
        address = discovery_info.address

        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()

        if not discovery_info.connectable:
            return self.async_abort(reason="not_connectable")

        if discovery_info.name or discovery_info.device.name:
            name = discovery_info.name or discovery_info.device.name
        else:
            short_address = address[-5:]
            name = f"KT6368A 防丢标签 ({short_address})"
        self._address = address
        self._name = name

        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict | None = None) -> FlowResult:
        """Confirm adding discovered device."""
        if self._discovery is None:
            return self.async_abort(reason="no_discovery_info")

        if user_input is not None:
            if user_input.get("confirm", False):
                address = self._address or self._discovery.address
                name = (
                    self._name
                    or self._discovery.name
                    or self._discovery.device.name
                    or address
                )

                return self.async_create_entry(
                    title=name,
                    data={CONF_ADDRESS: address, CONF_NAME: name},
                    options={
                        CONF_ALARM_ON_DISCONNECT: DEFAULT_ALARM_ON_DISCONNECT,
                        CONF_MAINTAIN_CONNECTION: DEFAULT_MAINTAIN_CONNECTION,
                        CONF_AUTO_RECONNECT: DEFAULT_AUTO_RECONNECT,
                        CONF_BATTERY_POLL_INTERVAL_MIN: DEFAULT_BATTERY_POLL_INTERVAL_MIN,
                    },
                )

        schema = vol.Schema({vol.Required("confirm", default=True): bool})
        address = self._address or self._discovery.address
        name = (
            self._name or self._discovery.name or self._discovery.device.name or address
        )
        return self.async_show_form(
            step_id="confirm",
            data_schema=schema,
            description_placeholders={
                "name": name,
                "address": address,
            },
        )

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Manual setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip()

            # 验证 BLE 地址格式
            if not is_valid_ble_address(address):
                errors[CONF_ADDRESS] = "invalid_ble_address"
                schema = vol.Schema(
                    {
                        vol.Required(CONF_ADDRESS): str,
                        vol.Optional(CONF_NAME): str,
                    }
                )
                return self.async_show_form(
                    step_id="user", data_schema=schema, errors=errors
                )

            name = user_input.get(CONF_NAME, address).strip()

            # 验证设备名称
            if not is_valid_device_name(name):
                errors[CONF_NAME] = "invalid_device_name"
                schema = vol.Schema(
                    {
                        vol.Required(CONF_ADDRESS): str,
                        vol.Optional(CONF_NAME): str,
                    }
                )
                return self.async_show_form(
                    step_id="user", data_schema=schema, errors=errors
                )

            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=name,
                data={CONF_ADDRESS: address, CONF_NAME: name},
                options={
                    CONF_ALARM_ON_DISCONNECT: DEFAULT_ALARM_ON_DISCONNECT,
                    CONF_MAINTAIN_CONNECTION: DEFAULT_MAINTAIN_CONNECTION,
                    CONF_AUTO_RECONNECT: DEFAULT_AUTO_RECONNECT,
                    CONF_BATTERY_POLL_INTERVAL_MIN: DEFAULT_BATTERY_POLL_INTERVAL_MIN,
                },
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): str,
                vol.Optional(CONF_NAME): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opts = self.entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ALARM_ON_DISCONNECT,
                    default=opts.get(
                        CONF_ALARM_ON_DISCONNECT, DEFAULT_ALARM_ON_DISCONNECT
                    ),
                ): bool,
                vol.Required(
                    CONF_MAINTAIN_CONNECTION,
                    default=opts.get(
                        CONF_MAINTAIN_CONNECTION, DEFAULT_MAINTAIN_CONNECTION
                    ),
                ): bool,
                vol.Required(
                    CONF_AUTO_RECONNECT,
                    default=opts.get(CONF_AUTO_RECONNECT, DEFAULT_AUTO_RECONNECT),
                ): bool,
                vol.Required(
                    CONF_BATTERY_POLL_INTERVAL_MIN,
                    default=opts.get(
                        CONF_BATTERY_POLL_INTERVAL_MIN,
                        DEFAULT_BATTERY_POLL_INTERVAL_MIN,
                    ),
                ): vol.All(int, vol.Range(min=5, max=7 * 24 * 60)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


@callback
def async_get_options_flow(
    config_entry: config_entries.ConfigEntry,
) -> OptionsFlowHandler:
    return OptionsFlowHandler(config_entry)
