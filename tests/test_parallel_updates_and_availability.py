"""Test PARALLEL_UPDATES configuration and availability management."""

import pytest
from unittest.mock import Mock, patch

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.button import ButtonEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant

from custom_components.anti_loss_tag.binary_sensor import (
    AntiLossTagBinaryBase,
    AntiLossTagButtonBinarySensor,
    AntiLossTagDisconnectBinarySensor,
)
from custom_components.anti_loss_tag.button import (
    AntiLossTagStartAlarmButton,
    AntiLossTagStopAlarmButton,
)
from custom_components.anti_loss_tag.sensor import AntiLossTagBatterySensor
from custom_components.anti_loss_tag.switch import AntiLossTagDisconnectAlarmSwitch


class TestParallelUpdatesConfiguration:
    """Test that all platform entities have PARALLEL_UPDATES configured."""

    def test_binary_sensor_has_parallel_updates(self) -> None:
        """Test that binary sensor declares PARALLEL_UPDATES."""
        # Check class attribute exists
        assert hasattr(AntiLossTagBinaryBase, "PARALLEL_UPDATES")
        # Should be 0 for read-only entities (updates are centralized)
        assert AntiLossTagBinaryBase.PARALLEL_UPDATES == 0

    def test_sensor_has_parallel_updates(self) -> None:
        """Test that sensor declares PARALLEL_UPDATES."""
        assert hasattr(AntiLossTagBatterySensor, "PARALLEL_UPDATES")
        # Should be 0 for read-only entities
        assert AntiLossTagBatterySensor.PARALLEL_UPDATES == 0

    def test_button_has_parallel_updates(self) -> None:
        """Test that button declares PARALLEL_UPDATES."""
        # Both button types should have the same restriction
        assert hasattr(AntiLossTagStartAlarmButton, "PARALLEL_UPDATES")
        assert hasattr(AntiLossTagStopAlarmButton, "PARALLEL_UPDATES")
        # Should be 1 for action entities to prevent concurrent writes
        assert AntiLossTagStartAlarmButton.PARALLEL_UPDATES == 1
        assert AntiLossTagStopAlarmButton.PARALLEL_UPDATES == 1

    def test_switch_has_parallel_updates(self) -> None:
        """Test that switch declares PARALLEL_UPDATES."""
        assert hasattr(AntiLossTagDisconnectAlarmSwitch, "PARALLEL_UPDATES")
        # Should be 1 for action entities
        assert AntiLossTagDisconnectAlarmSwitch.PARALLEL_UPDATES == 1


class TestAvailabilitySingleEntry:
    """Test that availability state is managed through a single entry point."""

    @pytest.fixture
    def mock_device(self) -> Mock:
        """Create a mock device instance."""
        device = Mock()
        device.address = "AA:BB:CC:DD:EE:FF"
        device._available = True
        device._connected = False
        device._rssi = -50
        device._battery = 85
        return device

    def test_update_availability_changes_state(self, mock_device: Mock) -> None:
        """Test that _update_availability actually changes the state."""
        from custom_components.anti_loss_tag.device import AntiLossTagDevice

        # Create a real device instance with mocked dependencies
        with patch("custom_components.anti_loss_tag.device.BleConnectionManager"):
            hass = Mock(spec=HomeAssistant)
            entry = Mock()
            entry.data = {"address": "AA:BB:CC:DD:EE:FF", "name": "Test Device"}
            entry.options = {}
            entry.runtime_data = None

            device = AntiLossTagDevice(hass, entry)
            assert device._available is False  # Initial state

            # Test setting to True
            device._update_availability(True)
            assert device._available is True

            # Test setting to False
            device._update_availability(False)
            assert device._available is False

            # Test that setting same value doesn't trigger update (no exception)
            device._update_availability(False)
            assert device._available is False

    def test_update_availability_logs_changes(self, mock_device: Mock) -> None:
        """Test that availability changes are logged."""
        from custom_components.anti_loss_tag.device import AntiLossTagDevice
        import logging

        with patch("custom_components.anti_loss_tag.device.BleConnectionManager"):
            hass = Mock(spec=HomeAssistant)
            entry = Mock()
            entry.data = {"address": "AA:BB:CC:DD:EE:FF", "name": "Test Device"}
            entry.options = {}
            entry.runtime_data = None

            device = AntiLossTagDevice(hass, entry)

            # Mock the logger to capture debug calls
            with patch.object(device._LOGGER, "debug") as mock_debug:
                device._update_availability(True)
                # Should log when state actually changes
                assert mock_debug.call_count == 1
                assert "AVAILABLE" in str(mock_debug.call_args)

                # Setting same value should not log
                mock_debug.reset_mock()
                device._update_availability(True)
                assert mock_debug.call_count == 0

    def test_no_direct_available_assignment_in_code(self) -> None:
        """Test that _available is only set through _update_availability."""
        import subprocess
        import re

        # Search for direct assignments to _available in device.py
        result = subprocess.run(
            [
                "grep",
                "-n",
                "self._available =",
                "custom_components/anti_loss_tag/device.py",
            ],
            capture_output=True,
            text=True,
        )

        # The only assignment should be in _update_availability method
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        for line in lines:
            # Allow the assignment in _update_availability and the property definition
            if (
                "_update_availability" in line
                or "@property" in line
                or "def available" in line
            ):
                continue
            # If we find any other direct assignment, fail the test
            assert False, f"Found direct _available assignment: {line}"


class TestEntityAvailabilityConsistency:
    """Test that entity availability is consistent with device state."""

    def test_binary_sensor_available_when_device_available(self) -> None:
        """Test that binary_sensor availability reflects device state."""
        mock_device = Mock()
        mock_device.available = True
        mock_device.connected = False

        sensor = AntiLossTagButtonBinarySensor(mock_device)
        assert sensor.available is True

        mock_device.available = False
        assert sensor.available is False

    def test_button_available_when_device_available_or_connected(self) -> None:
        """Test that button availability allows operations when connected."""
        mock_device = Mock()
        mock_device.available = False
        mock_device.connected = True

        button = AntiLossTagStartAlarmButton(mock_device)
        # Button should be available if device is connected (for on-demand operations)
        assert button.available is True

    def test_sensor_available_only_with_battery_data(self) -> None:
        """Test that battery sensor availability requires battery data."""
        mock_device = Mock()
        mock_device.battery = None
        mock_device.available = True

        sensor = AntiLossTagBatterySensor(mock_device)
        assert sensor.available is False

        mock_device.battery = 85
        assert sensor.available is True

    def test_switch_availability_consistency(self) -> None:
        """Test that switch availability is consistent."""
        mock_device = Mock()
        mock_device.available = True
        mock_device.connected = False

        switch = AntiLossTagDisconnectAlarmSwitch(mock_device)
        assert switch.available is True
