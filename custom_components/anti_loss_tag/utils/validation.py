"""输入验证工具模块。"""

from __future__ import annotations

import re
import logging

_LOGGER = logging.getLogger(__name__)

# BLE 地址验证模式
# 支持 MAC 地址格式：XX:XX:XX:XX:XX:XX 或 XX-XX-XX-XX-XX-XX
# 支持匿名地址（较短）
MAC_ADDRESS_PATTERN = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")
ANONYMOUS_ADDRESS_PATTERN = re.compile(r"^([0-9A-Fa-f]{2}[:-]){2}[0-9A-Fa-f]{2}$")

# GATT handle 范围
MIN_GATT_HANDLE = 0
MAX_GATT_HANDLE = 0xFFFF  # BLE handle 是 16 位


def is_valid_ble_address(address: str) -> bool:
    """验证 BLE 地址格式。

    Args:
        address: 待验证的 BLE 地址字符串

    Returns:
        True 如果地址格式有效，False 否外

    Examples:
        >>> is_valid_ble_address("AA:BB:CC:DD:EE:FF")
        True
        >>> is_valid_ble_address("aa-bb-cc-dd-ee-ff")
        True
        >>> is_valid_ble_address("AA:BB:CC:DD:EE")
        False
        >>> is_valid_ble_address("GG:HH:II:JJ:KK:LL")
        False
    """
    if not address or not isinstance(address, str):
        return False

    address = address.strip()

    # 尝试匹配标准 MAC 地址
    if MAC_ADDRESS_PATTERN.match(address):
        return True

    # 尝试匹配匿名地址
    if ANONYMOUS_ADDRESS_PATTERN.match(address):
        return True

    return False


def is_valid_device_name(name: str) -> bool:
    """验证设备名称。

    Args:
        name: 设备名称

    Returns:
        True 如果名称有效，False 否外
    """
    if not name or not isinstance(name, str):
        return False

    # 移除首尾空白
    name = name.strip()

    # 检查长度（BLE 设备名称通常不超过 248 字节）
    if len(name) == 0 or len(name) > 248:
        return False

    # 检查是否包含控制字符（除空格、制表符外）
    for char in name:
        if ord(char) < 32 and char not in (" ", "\t"):
            return False

    return True


def normalize_ble_address(address: str) -> str:
    """标准化 BLE 地址格式（转为大写和冒号分隔）。

    Args:
        address: 原始地址

    Returns:
        标准化后的地址（XX:XX:XX:XX:XX:XX 格式）

    Raises:
        ValueError: 如果地址格式无效
    """
    if not is_valid_ble_address(address):
        raise ValueError(f"Invalid BLE address: {address}")

    # 移除所有分隔符，转为大写
    cleaned = address.replace(":", "").replace("-", "").upper()

    # 插入冒号分隔符
    return ":".join(cleaned[i : i + 2] for i in range(0, len(cleaned), 2))


def validate_gatt_handle(handle: int) -> bool:
    """验证 GATT handle 值。

    Args:
        handle: GATT handle 值

    Returns:
        True 如果 handle 在有效范围内，False 否外
    """
    if not isinstance(handle, int):
        return False
    return MIN_GATT_HANDLE <= handle <= MAX_GATT_HANDLE


def validate_battery_level(level: int) -> int | None:
    """验证并修正电池电量值。

    Args:
        level: 原始电量值

    Returns:
        修正后的电量值（0-100），如果无效返回 None
    """
    try:
        level_int = int(level)
        # 限制在有效范围
        return max(0, min(100, level_int))
    except (ValueError, TypeError):
        return None
