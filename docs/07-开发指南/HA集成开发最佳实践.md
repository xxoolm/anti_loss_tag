# Home Assistant 集成开发最佳实践

> **避免常见错误，遵循社区标准**  
> **基于 Home Assistant 2025.x 和最新开发规范**  
> **目标读者**：自定义集成开发者

---

## 一、项目结构

### 1.1 标准目录结构

```
custom_components/my_integration/
├── __init__.py              # 必须包含 async_setup_entry
├── manifest.json            # 集成元数据
├── config_flow.py           # 配置流程
├── const.py                 # 常量定义
├── manifest.json            # 集成元数据（版本、依赖等）
├── strings.json             # UI 字符串翻译
├── services.yaml            # 服务定义
├── translations/            # 多语言翻译
│   └── en.json
├── device.py                # 设备类（可选）
├── entity.py                # 实体类（可选）
└── tests/                   # 单元测试
    ├── __init__.py
    ├── conftest.py
    └── test_*.py
```

### 1.2 manifest.json 必需字段

```json
{
  "domain": "my_integration",
  "name": "My Integration",
  "codeowners": ["@github_username"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/user/my_integration",
  "iot_class": "local_polling",
  "requirements": ["bleak>=2.1.0"],
  "version": "1.0.0"
}
```

---

## 二、Config Flow 最佳实践

### 2.1 基本结构

```python
"""Config flow for my_integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from . import DOMAIN
from .const import CONF_MAC_ADDRESS, CONF_NAME


class MyIntegrationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for my_integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # 验证输入
            if not self._validate_mac(user_input[CONF_MAC_ADDRESS]):
                errors["base"] = "invalid_mac"
            else:
                # 创建配置条目
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input
                )
        
        # 显示表单
        data_schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_MAC_ADDRESS): str,
        })
        
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )
    
    def _validate_mac(self, mac: str) -> bool:
        """验证 MAC 地址格式。"""
        import re
        pattern = r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
        return re.match(pattern, mac) is not None
```

---

### 2.2 Options Flow（更新配置）

```python
"""Options flow for my_integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from . import DOMAIN
from .const import (
    CONF_BATTERY_POLL_INTERVAL,
    CONF_RSSI_POLL_INTERVAL,
    DEFAULT_BATTERY_POLL_INTERVAL,
    DEFAULT_RSSI_POLL_INTERVAL,
)


class MyIntegrationOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for my_integration."""

    async def async_step_init(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        
        options = self.config_entry.options or {}
        data_schema = vol.Schema({
            vol.Optional(
                CONF_BATTERY_POLL_INTERVAL,
                default=options.get(
                    CONF_BATTERY_POLL_INTERVAL,
                    DEFAULT_BATTERY_POLL_INTERVAL
                )
            ): int,
            vol.Optional(
                CONF_RSSI_POLL_INTERVAL,
                default=options.get(
                    CONF_RSSI_POLL_INTERVAL,
                    DEFAULT_RSSI_POLL_INTERVAL
                )
            ): int,
        })
        
        return self.async_show_form(
            step_id="init",
            data_schema=data_schema
        )
```

---

### 2.3 蓝牙设备的自动发现

```python
"""蓝牙设备发现的 Config Flow 示例。"""
from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfo,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import FlowResult


class BLEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BLE device."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfo | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfo] = {}

    async def async_step_bluetooth(
        self,
        discovery_info: BluetoothServiceInfo,
    ) -> FlowResult:
        """Handle bluetooth discovery step."""
        self._discovery_info = discovery_info
        self._discovered_devices = async_discovered_service_info(self.hass)
        
        # 设置唯一 ID
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        
        return await self.async_step_confirm()
    
    async def async_step_confirm(
        self,
        user_input: dict[str, any] | None = None,
    ) -> FlowResult:
        """确认发现的设备。"""
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery_info.name,
                data={CONF_ADDRESS: self._discovery_info.address}
            )
        
        # 显示确认表单
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "name": self._discovery_info.name,
                "address": self._discovery_info.address,
            }
        )
```

---

## 三、async_setup_entry 最佳实践

### 3.1 基本模式

```python
"""__init__.py - 集成入口"""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """设置配置条目。"""
    _LOGGER.info("Setting up %s integration", DOMAIN)
    
    # 存储配置条目
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "device": None,  # 设备实例
        "coordinator": None,  # 数据更新协调器（可选）
    }
    
    # 前向设置实体
    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS
    )
    
    # 注册选项更新回调
    entry.async_on_unload(
        entry.add_update_listener(async_update_options)
    )
    
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """卸载配置条目。"""
    _LOGGER.info("Unloading %s integration", DOMAIN)
    
    # 卸载实体
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )
    
    if unload_ok:
        # 清理数据
        device = hass.data[DOMAIN][entry.entry_id].get("device")
        if device:
            await device.async_disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def async_update_options(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """更新选项。"""
    await hass.config_entries.async_reload(entry.entry_id)
```

---

### 3.2 错误处理和重试

```python
"""带错误处理的 setup 示例。"""
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """设置配置条目，带错误处理。"""
    host = entry.data[CONF_HOST]
    
    try:
        # 尝试连接设备
        device = await connect_to_device(host)
        
        # 验证认证
        if not device.is_authenticated:
            raise ConfigEntryAuthFailed("Authentication failed")
        
    except AuthenticationError as err:
        # 认证失败 - 触发重新认证流程
        raise ConfigEntryAuthFailed(
            f"Authentication failed for {host}: {err}"
        ) from err
    
    except (asyncio.TimeoutError, ConnectionError) as err:
        # 连接超时或错误 - 稍后重试
        raise ConfigEntryNotReady(
            f"Connection timeout to {host}: {err}"
        ) from err
    
    except Exception as err:
        # 其他错误
        _LOGGER.exception("Unexpected error setting up %s", DOMAIN)
        return False
    
    # 存储设备实例
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"device": device}
    
    # 前向设置实体
    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS
    )
    
    return True
```

---

### 3.3 使用 DataUpdateCoordinator

```python
"""使用数据更新协调器。"""
import asyncio
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryNotReady

_LOGGER = logging.getLogger(__name__)


class MyDeviceCoordinator(DataUpdateCoordinator):
    """我的设备数据更新协调器。"""

    def __init__(self, hass: HomeAssistant, device) -> None:
        """初始化协调器。"""
        super().__init__(
            hass,
            _LOGGER,
            name="My device coordinator",
            update_interval=timedelta(seconds=30),
        )
        self.device = device

    async def _async_update_data(self):
        """获取设备数据。"""
        try:
            # 获取最新数据
            data = await self.device.get_data()
            return data
        except Exception as err:
            _LOGGER.error("Error fetching data: %s", err)
            raise


# 在 async_setup_entry 中使用
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """设置配置条目。"""
    device = MyDevice(entry.data[CONF_HOST])
    
    # 创建协调器
    coordinator = MyDeviceCoordinator(hass, device)
    
    # 立即获取数据
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        raise
    except Exception as err:
        _LOGGER.error("Error setting up coordinator: %s", err)
        return False
    
    # 存储协调器
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "device": device,
    }
    
    # 前向设置实体
    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS
    )
    
    return True
```

---

## 四、实体开发最佳实践

### 4.1 传感器实体

```python
"""传感器实体示例。"""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .const import SENSOR_TYPES


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置传感器实体。"""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = [
        MySensor(coordinator, entry, sensor_type)
        for sensor_type in SENSOR_TYPES
    ]
    
    async_add_entities(entities)


class MySensor(SensorEntity):
    """我的传感器。"""

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        """初始化传感器。"""
        self.coordinator = coordinator
        self.entry = entry
        self.sensor_type = sensor_type
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_name = f"My {sensor_type}"
        self._attr_native_unit_of_measurement = SENSOR_TYPES[sensor_type]["unit"]

    @property
    def available(self) -> bool:
        """返回实体是否可用。"""
        return self.coordinator.last_update_success

    @property
    def native_value(self):
        """返回传感器值。"""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.sensor_type)

    async def async_update(self) -> None:
        """更新传感器（由协调器自动调用）。"""
        await self.coordinator.async_request_refresh()
```

---

### 4.2 使用 asyncio 避免阻塞

```python
"""避免阻塞事件循环。"""
import asyncio
from homeassistant.core import HomeAssistant

class BLEDevice:
    """BLE 设备类。"""
    
    def __init__(self, hass: HomeAssistant, address: str):
        self.hass = hass
        self.address = address
        self._client = None
        self._lock = asyncio.Lock()
    
    async def connect(self) -> None:
        """连接到设备（带锁保护）。"""
        async with self._lock:
            if self._client is not None:
                return
            
            self._client = BleakClient(self.address)
            await self._client.connect()
    
    async def disconnect(self) -> None:
        """断开连接。"""
        async with self._lock:
            if self._client is None:
                return
            
            await self._client.disconnect()
            self._client = None
    
    async def read_characteristic(self, uuid: str) -> bytes:
        """读取特征值。"""
        async with self._lock:
            if self._client is None:
                await self.connect()
            
            return await self._client.read_gatt_char(uuid)
```

---

## 五、蓝牙特定最佳实践

### 5.1 使用 bleak-retry-connector

```python
"""使用重试连接器提高可靠性。"""
from bleak import BleakClient
from bleak_retry_connector import (
    establish_connection,
    BleakError,
    BleakDBusError,
)

async def connect_to_device(address: str, max_attempts: int = 3):
    """连接到 BLE 设备，带重试。"""
    try:
        async with BleakClient(address) as client:
            await establish_connection(
                client,
                address,
                max_attempts=max_attempts,
                use_task_timeout=True,
            )
            return client
    except BleakError as err:
        _LOGGER.error("Failed to connect: %s", err)
        raise
    except BleakDBusError as err:
        if "org.bluez.Error.NotReady" in str(err):
            _LOGGER.error("Bluetooth adapter not ready")
        raise
```

---

### 5.2 蓝牙适配器管理

```python
"""检查蓝牙适配器可用性。"""
from homeassistant.components.bluetooth import (
    async_get_adapters,
    BluetoothServiceInfo,
)

async def check_bluetooth_adapter(hass: HomeAssistant) -> bool:
    """检查蓝牙适配器是否可用。"""
    adapters = await async_get_adapters(hass)
    
    if not adapters:
        _LOGGER.error("No Bluetooth adapters found")
        return False
    
    _LOGGER.info("Found %d Bluetooth adapter(s)", len(adapters))
    for adapter in adapters:
        _LOGGER.info(
            "Adapter: %s (%s)",
            adapter["name"],
            adapter["address"]
        )
    
    return True
```

---

### 5.3 处理蓝牙断开

```python
"""处理蓝牙断开重连。"""
from homeassistant.helpers.entity import Entity

class BLESensor(Entity):
    """蓝牙传感器，带自动重连。"""
    
    def __init__(self, device, address: str):
        self.device = device
        self.address = address
        self._connect_retries = 0
        self._max_retries = 3
    
    async def async_update(self) -> None:
        """更新传感器状态。"""
        try:
            # 尝试读取数据
            data = await self.device.read_data()
            self._connect_retries = 0  # 重置重试计数
            self._attr_available = True
        except (BleakError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Connection error: %s", err)
            
            # 尝试重连
            if self._connect_retries < self._max_retries:
                self._connect_retries += 1
                _LOGGER.info(
                    "Attempting to reconnect (%d/%d)",
                    self._connect_retries,
                    self._max_retries
                )
                await self.device.reconnect()
            else:
                _LOGGER.error("Max retries reached, giving up")
                self._attr_available = False
```

---

## 六、测试最佳实践

### 6.1 单元测试

```python
"""测试示例。"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.my_integration import async_setup_entry
from custom_components.my_integration.const import DOMAIN


@pytest.mark.asyncio
async def test_async_setup_entry(hass: HomeAssistant):
    """测试 async_setup_entry。"""
    # 创建模拟配置条目
    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.entry_id = "test_entry_id"
    config_entry.data = {
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "name": "Test Device",
    }
    config_entry.options = {}
    config_entry.add_update_listener = MagicMock()
    
    # 设置模拟
    hass.data = {}
    
    # 调用 setup
    result = await async_setup_entry(hass, config_entry)
    
    # 验证
    assert result is True
    assert DOMAIN in hass.data
    assert config_entry.entry_id in hass.data[DOMAIN]
```

---

### 6.2 集成测试

```python
"""集成测试示例。"""
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import EntityRegistry

from tests.common import MockConfigEntry


@pytest.mark.asyncio
async def test_sensor_entities(
    hass: HomeAssistant,
    entity_registry: EntityRegistry,
):
    """测试传感器实体。"""
    # 创建配置条目
    config_entry = MockConfigEntry(
        domain="my_integration",
        data={"mac_address": "AA:BB:CC:DD:EE:FF"},
        entry_id="test_entry",
    )
    config_entry.add_to_hass(hass)
    
    # 设置集成
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    
    # 验证实体创建
    entity_id = "sensor.my_sensor"
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "42"
```

---

## 七、常见错误模式（避免）

### 7.1 ❌ 错误：直接访问 hass.components

```python
# ❌ 错误
hass.components.websocket_api.async_register_command(...)

# ✅ 正确
from homeassistant.components import websocket_api
websocket_api.async_register_command(...)
```

### 7.2 ❌ 错误：使用已弃用的方法

```python
# ❌ 错误
hass.async_add_job(some_function)

# ✅ 正确
hass.async_create_task(some_function())
```

### 7.3 ❌ 错误：在 OptionsFlow 中设置 config_entry

```python
# ❌ 错误
class OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry  # 错误！

# ✅ 正确
class OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry  # 使用私有属性
```

### 7.4 ❌ 错误：未正确处理认证失败

```python
# ❌ 错误
async def async_setup_entry(hass, entry):
    try:
        device = await connect(entry.data["token"])
    except Exception:
        return False  # 不提供错误信息

# ✅ 正确
async def async_setup_entry(hass, entry):
    try:
        device = await connect(entry.data["token"])
    except AuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except ConnectionError as err:
        raise ConfigEntryNotReady(str(err)) from err
```

---

## 八、性能优化

### 8.1 减少轮询频率

```python
"""使用订阅而非轮询。"""
class MyCoordinator(DataUpdateCoordinator):
    """使用订阅的协调器。"""
    
    def __init__(self, hass, device):
        super().__init__(
            hass,
            _LOGGER,
            name="My coordinator",
            # 不需要 update_interval，因为我们使用订阅
        )
        self.device = device
        self._notification_callback = None
    
    async def _async_subscribe(self):
        """订阅设备通知。"""
        await self.device.subscribe(
            callback=self._async_handle_notification
        )
    
    def _async_handle_notification(self, data):
        """处理通知并更新数据。"""
        self.async_set_updated_data(data)
```

---

### 8.2 缓存数据

```python
"""缓存设备服务信息。"""
from functools import lru_cache

@lru_cache(maxsize=128)
def get_service_uuids(device_type: str) -> list[str]:
    """获取设备的服务 UUID（缓存）。"""
    return SERVICE_UUIDS.get(device_type, [])
```

---

## 九、文档和发布

### 9.1 README.md 模板

```markdown
# My Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

## 功能

- 功能1
- 功能2

## 安装

1. 通过 HACS 安装
2. 重启 Home Assistant
3. 在设置中配置

## 配置

```yaml
# configuration.yaml
my_integration:
  host: "192.168.1.100"
```

## 故障排除

### 问题1
**症状**：...
**解决方法**：...
```

---

### 9.2 发布检查清单

- [ ] 版本号更新（manifest.json, __init__.py, 标签）
- [ ] CHANGELOG.md 更新
- [ ] 所有测试通过
- [ ] 文档更新
- [ ] 代码审查
- [ ] 创建 GitHub Release

---

**最后更新**：2025-03-06  
**相关文档**：[BLE开发常见问题](./BLE开发常见问题.md)  
**官方指南**：[Home Assistant Developer Docs](https://developers.home-assistant.io/)
