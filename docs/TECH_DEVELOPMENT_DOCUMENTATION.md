# Home Assistant自定义集成技术开发文档

基于官方规范和社区最佳实践（2025年最新）

---

## 1. 项目概述

本文档总结Home Assistant自定义集成开发的官方规范、成熟示例和主流技术方案，为anti_loss_tag项目提供技术参考。

---

## 2. 官方规范（Home Assistant Developers）

### 2.1 集成文件结构

**最小必需文件**：
```
custom_components/<domain>/
├── __init__.py           # 集成入口
├── manifest.json         # 集成元数据（必需）
├── config_flow.py        # 配置流程（如果config_flow: true）
├── const.py              # 常量定义
└── translations/         # 翻译文件
    ├── en.json
    └── zh-Hans.json
```

**推荐分层结构**：
```
custom_components/<domain>/
├── __init__.py
├── manifest.json
├── const.py
├── config_flow.py
├── coordinator.py        # DataUpdateCoordinator（多实体共享数据）
├── device/               # 设备管理（可选）
│   ├── __init__.py
│   └── state_machine.py
└── platforms/            # 平台实体
    ├── sensor.py
    ├── binary_sensor.py
    └── ...
```

### 2.2 manifest.json规范（2025）

**必需字段**：
```json
{
  "domain": "your_domain",                    // 域名（唯一标识符）
  "name": "Your Integration Name",            // 显示名称
  "codeowners": ["@username"],                 // GitHub用户名（至少一个）
  "config_flow": true,                         // 是否支持UI配置
  "integration_type": "device",                // 集成类型（2025新增）
  "iot_class": "local_push",                   // IoT类别
  "documentation": "https://github.com/...",   // 文档链接
  "issue_tracker": "https://github.com/.../issues",
  "requirements": [],                          // Python依赖
  "dependencies": [],                          // HA依赖
  "version": "1.0.0"                           // 版本号
}
```

**integration_type**选项（2025新增，必需）：
- `device` - 提供单个设备（如ESPHome）
- `hub` - 提供集线器，管理多个设备（如Philips Hue）
- `service` - 单个服务（无设备）
- `virtual` - 虚拟集成
- `system` - 系统集成
- `helper` - 帮助实体
- `hardware` - 硬件集成
- `automation` - 自动化集成

**iot_class**选项：
- `local_polling` - 直接通信，轮询状态（可能有延迟）
- `local_push` - 直接通信，设备主动通知（立即更新）
- `cloud_polling` - 云端轮询
- `cloud_push` - 云端推送

**蓝牙集成特殊字段**：
```json
{
  "dependencies": ["bluetooth_adapters"],
  "bluetooth": [
    {
      "service_uuid": "0000ffe0-0000-1000-8000-00805f9b34fb",
      "connectable": true
    }
  ]
}
```

### 2.3 Config Flow规范

**基本结构**：
```python
class MyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """手动配置步骤"""
        if user_input is not None:
            await self.async_set_unique_id(user_input["address"])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input["name"], data=user_input)

        return self.async_show_form(step_id="user", data_schema=vol.Schema({...}))

    async def async_step_bluetooth(self, discovery_info):
        """蓝牙发现步骤"""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        return await self.async_step_confirm()
```

**关键要点**：
1. **unique_id**：必须设置，防止重复配置
2. **discovery**：支持蓝牙/网络发现
3. **options**：配置后可修改的选项
4. **翻译**：在`translations/strings.json`中定义UI文本

### 2.4 数据获取模式

**DataUpdateCoordinator（推荐）**：
```python
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

class MyCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, device):
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=f"{DOMAIN}-{device.address}",
            update_interval=timedelta(seconds=30),  # None表示仅手动刷新
        )
        self.device = device

    async def _async_update_data(self):
        """获取数据"""
        return await self.device.fetch_data()
```

**优点**：
- 多实体共享数据，减少API调用
- 自动处理速率限制
- 提供一致的更新机制

**首次刷新**：
```python
async def async_setup_entry(hass, entry):
    coordinator = MyCoordinator(hass, device)
    await coordinator.async_config_entry_first_refresh()  # 首次刷新
    hass.data[DOMAIN][entry.entry_id] = coordinator
```

### 2.5 蓝牙集成最佳实践

**依赖管理**：
```json
{
  "dependencies": ["bluetooth_adapters"],
  "requirements": ["bleak>=0.21.0", "bleak-retry-connector>=3.0.0"]
}
```

**使用HA Scanner**：
```python
from homeassistant.components import bluetooth

scanner = bluetooth.async_get_scanner(hass)
device = await scanner.find_device_by_address(address)
```

**连接管理**：
- **连接超时**：至少10秒（BlueZ需要解析服务）
- **重试机制**：使用`bleak-retry-connector`
- **槽位管理**：ESPHome代理只有2-3个槽位
- **不要复用客户端**：每个连接使用新的BleakClient

**bleak-retry-connector用法**：
```python
from bleak_retry_connector import establish_connection, BleakClientWithServiceCache

client = await establish_connection(
    client_class=BleakClientWithServiceCache,  # 使用服务缓存
    device=device,
    name="Device Name",
    max_attempts=4,  # 最多重试4次
    use_services_cache=True,  # 启用服务缓存
)
```

---

## 3. 成熟示例

### 3.1 官方示例
- **home-assistant/example-custom-config** - 官方示例集合
- **jpawlowski/hacs.integration_blueprint** - 现代化模板（包含CI/CD、测试）

### 3.2 社区成熟仓库
- **libdyson-wg/ha-dyson** - 完整的工程化结构
- **Bluetooth-Devices/bleak-retry-connector** - BLE连接最佳实践

### 3.3 代码质量标准
- 使用async/await模式
- 实现proper error handling
- 遵循命名约定
- 使用Type Hints
- 分离API逻辑和集成逻辑

---

## 4. 异步编程模式

### 4.1 基本原则
- 所有核心方法有async版本
- 基于asyncio模块
- 访问受限（只有async上下文可访问核心API）

### 4.2 完整示例
```python
from homeassistant.core import HomeAssistant

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """设置集成"""
    # 创建协调器
    coordinator = MyCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    # 存储数据
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # 设置平台
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True
```

---

## 5. 平台实体开发

### 5.1 实体基类
```python
from homeassistant.helpers.entity import Entity

class MyEntity(Entity):
    def __init__(self, device):
        self._device = device

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.address)},
            name=self._device.name,
            manufacturer="Manufacturer",
            model="Model",
        )

    @property
    def unique_id(self):
        return f"{self._device.address}_sensor"

    @property
    def available(self):
        return self._device.available
```

### 5.2 监听设备更新
```python
async def async_added_to_hass(self):
    self._unsub = self._device.async_add_listener(self.async_write_ha_state)

async def async_will_remove_from_hass(self):
    if self._unsub:
        self._unsub()
```

---

## 6. 测试与验证

### 6.1 语法检查
```bash
python3 -m compileall custom_components/your_integration
```

### 6.2 开发环境
- 使用Dev Container（推荐）
- 运行`scripts/develop`启动HA
- 访问 http://localhost:8123

---

## 7. 发布流程

### 7.1 HACS要求
- Public GitHub仓库
- Valid hacs.json
- Valid manifest.json
- 至少一个release
- 注册在home-assistant/brands

### 7.2 质量标准
- Bronze级别（最低）
  - 配置流程完成
  - 基本功能工作
  - 基本文档

- Silver级别（推荐）
  - 完整文档
  - 诊断信息
  - 故障排除指南

---

## 8. 关键注意事项

### 8.1 常见错误
1. **忽略unique_id** - 导致重复配置
2. **阻塞操作** - 使用同步代码阻塞事件循环
3. **硬编码** - 配置应该可配置
4. **缺少错误处理** - 导致集成崩溃

### 8.2 性能优化
1. 使用DataUpdateCoordinator共享数据
2. 避免频繁轮询
3. 使用always_update=False降低重复写
4. 缓存服务发现

### 8.3 蓝牙特殊考虑
1. ESPHome代理槽位限制（2-3个）
2. 连接不稳定是常态
3. 使用bleak-retry-connector处理重试
4. 实现连接槽位管理

---

## 9. 参考资源

### 9.1 官方文档
- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Creating your first integration](https://developers.home-assistant.io/docs/creating_component_index/)
- [Bluetooth integration](https://developers.home-assistant.io/docs/bluetooth/)
- [Integration quality scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/)

### 9.2 社区资源
- [Home Assistant Community](https://community.home-assistant.io/)
- [Discord #dev_bluetooth](https://discord.gg/home-assistant)
- [GitHub Discussions](https://github.com/home-assistant/core/discussions)

### 9.3 代码示例
- [example-custom-config](https://github.com/home-assistant/example-custom-config)
- [integration_blueprint](https://github.com/jpawlowski/hacs.integration_blueprint)
- [bleak-retry-connector](https://github.com/Bluetooth-Devices/bleak-retry-connector)

---

## 10. 总结

Home Assistant自定义集成开发需要遵循严格的规范和最佳实践：

1. **文件结构** - 标准化的目录布局
2. **manifest.json** - 2025年新要求（integration_type等）
3. **Config Flow** - UI配置流程
4. **DataUpdateCoordinator** - 多实体数据共享
5. **蓝牙集成** - 使用bleak-retry-connector
6. **异步编程** - 全面使用async/await
7. **平台实体** - Sensor、BinarySensor等
8. **测试验证** - 语法检查、开发环境
9. **发布流程** - HACS、质量标准
10. **性能优化** - 缓存、共享数据、避免轮询

遵循这些规范可以开发出高质量、可维护的自定义集成。
