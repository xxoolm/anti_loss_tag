# SPDX-License-Identifier: MIT
"""Shared entity mixins for AntiLossTag integration."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


class AntiLossTagEntityMixin:
    """Mixin providing common device info for AntiLossTag entities."""

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._dev.address)},
            name=self._dev.name,
            manufacturer="Unknown",
            model="BLE Anti-Loss Tag",
        )
