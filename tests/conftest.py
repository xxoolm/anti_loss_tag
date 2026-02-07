"""测试配置文件."""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


@pytest.fixture
async def hass():
    """Fixture to provide a test instance of Home Assistant."""
    hass = HomeAssistant("/tmpfakeconfigdir")
    await hass.async_start()
    await hass.async_block_till_done()
    yield hass
    await hass.async_stop()


@pytest.fixture
def mock_ble_device():
    """Fixture to provide a mock BLE device."""
    return {
        "address": "AA:BB:CC:DD:EE:FF",
        "name": "Test Tag",
        "rssi": -60,
        "manufacturer_data": {},
        "service_data": {},
        "service_uuids": [],
    }
