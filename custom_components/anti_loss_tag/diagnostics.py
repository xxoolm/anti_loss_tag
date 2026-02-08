"""Diagnostics support for anti_loss_tag integration."""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr

from . import BleConnectionManager
from .const import (
    ADDRESS,
    CONF_ALARM_ON_DISCONNECT,
    CONF_AUTO_RECONNECT,
    CONF_BATTERY_POLL_INTERVAL_MIN,
    CONF_MAINTAIN_CONNECTION,
    DEFAULT_ALARM_ON_DISCONNECT,
    DEFAULT_AUTO_RECONNECT,
    DEFAULT_BATTERY_POLL_INTERVAL_MIN,
    DEFAULT_MAINTAIN_CONNECTION,
    DOMAIN,
    NAME,
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    This function provides comprehensive diagnostic information about the device
    and integration state, useful for debugging and troubleshooting.

    Sensitive information (like exact device address) is partially redacted.
    """
    device = entry.runtime_data
    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)

    # Get entities for this config entry
    entities = [
        {
            "entity_id": entity.entity_id,
            "unique_id": entity.unique_id,
            "platform": entity.platform,
            "disabled": entity.disabled,
            "disabled_by": entity.disabled_by,
        }
        for entity in er.async_entries_for_config_entry(entity_reg, entry.entry_id)
    ]

    # Get device info
    hass_device = device_reg.async_get_device({(DOMAIN, device.address)})
    device_info = {}
    if hass_device:
        device_info = {
            "name": hass_device.name,
            "name_by_user": hass_device.name_by_user,
            "model": hass_device.model,
            "manufacturer": hass_device.manufacturer,
            "sw_version": hass_device.sw_version,
            "area_id": hass_device.area_id,
            "identifiers": [
                list(identifiers) for identifiers in hass_device.identifiers
            ],
        }

    # Get connection manager stats (if available)
    conn_mgr_info = {}
    if DOMAIN in hass.data and "_conn_mgr" in hass.data[DOMAIN]:
        conn_mgr: BleConnectionManager | None = hass.data[DOMAIN].get("_conn_mgr")
        if conn_mgr and hasattr(conn_mgr, "_semaphore"):
            conn_mgr_info = {
                "max_connections": conn_mgr._semaphore._value
                if conn_mgr._semaphore
                else "unknown",
                "connection_slots_available": conn_mgr._semaphore._value
                if conn_mgr._semaphore
                else "unknown",
            }

    # Redact sensitive address (show only first 6 chars)
    address_redacted = device.address[:6] + "****" if device.address else None

    return {
        "entry_data": {
            NAME: entry.data.get(NAME),
            ADDRESS: address_redacted,
        },
        "options": {
            CONF_MAINTAIN_CONNECTION: entry.options.get(
                CONF_MAINTAIN_CONNECTION, DEFAULT_MAINTAIN_CONNECTION
            ),
            CONF_AUTO_RECONNECT: entry.options.get(
                CONF_AUTO_RECONNECT, DEFAULT_AUTO_RECONNECT
            ),
            CONF_ALARM_ON_DISCONNECT: entry.options.get(
                CONF_ALARM_ON_DISCONNECT, DEFAULT_ALARM_ON_DISCONNECT
            ),
            CONF_BATTERY_POLL_INTERVAL_MIN: entry.options.get(
                CONF_BATTERY_POLL_INTERVAL_MIN, DEFAULT_BATTERY_POLL_INTERVAL_MIN
            ),
        },
        "device_state": {
            "available": device.available,
            "connected": device._connected,
            "rssi": device.rssi,
            "battery": device.battery,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "last_battery_read": (
                device.last_battery_read.isoformat()
                if device.last_battery_read
                else None
            ),
            "last_error": device.last_error,
            "maintain_connection": device.maintain_connection,
            "auto_reconnect": device.auto_reconnect,
            "alarm_on_disconnect": device.alarm_on_disconnect,
            "battery_poll_interval": device.battery_poll_interval,
        },
        "connection_state": {
            "client_exists": device._client is not None,
            "conn_slot_acquired": device._conn_slot_acquired,
            "connect_fail_count": device._connect_fail_count,
            "cooldown_active": device._cooldown_until_ts > 0,
            "cached_characteristics": len(device._cached_chars)
            if device._cached_chars
            else 0,
            "battery_task_running": device._battery_task is not None
            and not device._battery_task.done(),
            "connect_task_running": device._connect_task is not None
            and not device._connect_task.done(),
        },
        "connection_manager": conn_mgr_info,
        "device_info": device_info,
        "entities": entities,
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device_id: str
) -> dict[str, Any]:
    """Return diagnostics for a device.

    This is an alternative entry point that can be used if we want
    device-level diagnostics in addition to config entry diagnostics.
    """
    # For now, we'll delegate to config entry diagnostics
    return await async_get_config_entry_diagnostics(hass, entry)
