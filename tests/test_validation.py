"""测试输入验证工具."""

import pytest
from custom_components.anti_loss_tag.utils.validation import (
    is_valid_ble_address,
    is_valid_device_name,
    is_valid_gatt_handle,
    is_valid_battery_level,
)


class TestBLEAddressValidation:
    """测试 BLE 地址验证."""

    def test_valid_mac_address_with_colons(self):
        """测试有效的 MAC 地址（冒号分隔）."""
        assert is_valid_ble_address("AA:BB:CC:DD:EE:FF") is True
        assert is_valid_ble_address("00:11:22:33:44:55") is True
        assert is_valid_ble_address("aa:bb:cc:dd:ee:ff") is True  # 小写

    def test_valid_mac_address_with_hyphens(self):
        """测试有效的 MAC 地址（连字符分隔）."""
        assert is_valid_ble_address("AA-BB-CC-DD-EE-FF") is True
        assert is_valid_ble_address("00-11-22-33-44-55") is True

    def test_invalid_mac_address(self):
        """测试无效的 MAC 地址."""
        assert is_valid_ble_address("AA:BB:CC:DD:EE") is False  # 太短
        assert is_valid_ble_address("AA:BB:CC:DD:EE:FF:GG") is False  # 太长
        assert is_valid_ble_address("AA:BB:CC:DD:EE:GG") is False  # 无效字符
        assert is_valid_ble_address("") is False  # 空字符串
        assert is_valid_ble_address("invalid") is False  # 完全无效
        assert is_valid_ble_address(None) is False  # None

    def test_mac_address_with_spaces(self):
        """测试带空格的 MAC 地址."""
        assert is_valid_ble_address(" AA:BB:CC:DD:EE:FF ") is True  # 会被 strip
        assert is_valid_ble_address("AA : BB:CC:DD:EE:FF") is False  # 内部空格


class TestDeviceNameValidation:
    """测试设备名称验证."""

    def test_valid_device_names(self):
        """测试有效的设备名称."""
        assert is_valid_device_name("My Tag") is True
        assert is_valid_device_name("测试标签") is True
        assert is_valid_device_name("Tag-123") is True
        assert is_valid_device_name("A" * 100) is True

    def test_invalid_device_names(self):
        """测试无效的设备名称."""
        assert is_valid_device_name("") is False  # 空字符串
        assert is_valid_device_name("   ") is False  # 仅空格
        assert is_valid_device_name(None) is False  # None
        assert is_valid_device_name("Tag\x00\x01") is False  # 包含控制字符
        assert is_valid_device_name("A" * 300) is False  # 超过最大长度

    def test_device_name_with_control_characters(self):
        """测试包含控制字符的设备名称."""
        assert is_valid_device_name("Tag\nNewline") is False
        assert is_valid_device_name("Tag\tTab") is False
        assert is_valid_device_name("Tag\rReturn") is False


class TestGATTHandleValidation:
    """测试 GATT 句柄验证."""

    def test_valid_handles(self):
        """测试有效的 GATT 句柄."""
        assert is_valid_gatt_handle(0) is True
        assert is_valid_gatt_handle(1) is True
        assert is_valid_gatt_handle(255) is True
        assert is_valid_gatt_handle(65535) is True

    def test_invalid_handles(self):
        """测试无效的 GATT 句柄."""
        assert is_valid_gatt_handle(-1) is False
        assert is_valid_gatt_handle(65536) is False
        assert is_valid_gatt_handle(None) is False


class TestBatteryLevelValidation:
    """测试电池电量验证."""

    def test_valid_battery_levels(self):
        """测试有效的电池电量."""
        assert is_valid_battery_level(0) is True
        assert is_valid_battery_level(50) is True
        assert is_valid_battery_level(100) is True

    def test_invalid_battery_levels(self):
        """测试无效的电池电量."""
        assert is_valid_battery_level(-1) is False
        assert is_valid_battery_level(101) is False
        assert is_valid_battery_level(None) is False
        assert is_valid_battery_level(150) is False
