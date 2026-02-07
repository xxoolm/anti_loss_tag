# AGENTS.md - Home Assistant 防丢标签集成开发指南

本文档为 AI 编码助手（agentic coding agents）提供项目规范和最佳实践。

## 项目概述

- **类型**: Home Assistant 自定义集成（BLE 防丢标签）
- **语言**: Python 3.11+
- **主要依赖**: bleak >= 0.21.0, bleak-retry-connector >= 3.0.0
- **代码位置**: `custom_components/anti_loss_tag/`

---

## 1. 构建、Lint 和测试命令

### 本地开发

```bash
# 开发时将代码复制到 Home Assistant 自定义组件目录
cp -r custom_components/anti_loss_tag ~/.homeassistant/custom_components/

# 重启 Home Assistant 或重新加载配置
# 在 HA 中：配置 → 系统 → 服务器管理 → 重新加载核心 → YAML 配置重新加载
```

### 代码质量检查（建议添加）

```bash
# 格式化代码（如果添加 ruff）
ruff check --fix custom_components/anti_loss_tag/
ruff format custom_components/anti_loss_tag/

# 类型检查（如果添加 mypy）
mypy custom_components/anti_loss_tag/

# Home Assistant 配置验证
hass --script check_config --path ~/.homeassistant
```

### 运行单个测试（未来）

```bash
# 当前无测试。如需添加，创建 tests/ 目录：
# pytest tests/test_device.py::test_connection -v
# pytest tests/test_sensor.py::TestBatterySensor -v
```

---

## 2. 代码风格规范

### 2.1 导入顺序（严格）

```python
# 第 1 行：所有文件必须有
from __future__ import annotations

# 标准库
import asyncio
import logging
from collections.abc import Callable
from datetime import datetime

# 第三方库
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from bleak.exc import BleakError

# 本地模块（. 前缀）
from .const import DOMAIN, CONF_ADDRESS
from .device import AntiLossTagDevice
```

### 2.2 类型注解（必须）

- **所有函数**必须有返回类型
- 使用 PEP 604 语法：`int | None` 而非 `Optional[int]`
- 集合类型：`list[str]`、`dict[str, int]`、`set[Callable[[], None]]`

```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """必须有 docstring 和类型注解。"""
    pass

@property
def battery(self) -> int | None:
    """属性也需要类型注解。"""
    return self._battery
```

### 2.3 命名约定

| 类型 | 规则 | 示例 |
|------|------|------|
| 类名 | PascalCase | `AntiLossTagDevice`, `OptionsFlowHandler` |
| 函数/方法 | snake_case | `async_setup_entry`, `_async_write_bytes` |
| 私有成员 | _前缀 | `_client`, `_connected`, `_battery` |
| 常量 | UPPER_SNAKE_CASE | `DOMAIN`, `UUID_NOTIFY_FFE1` |
| 属性 | @property, 无下划线 | `available`, `connected`, `battery` |

### 2.4 异步编程模式

```python
# HA 集成方法必须是 async
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    device = AntiLossTagDevice(hass, entry)
    await device.async_maybe_connect_initial()

# 回调使用 @callback（非 async）
@callback
def _async_on_bluetooth_event(self, service_info, change) -> None:
    self._available = True
    self._async_dispatch_update()

# 锁保护共享状态
async def async_ensure_connected(self) -> None:
    async with self._connect_lock:
        # 连接逻辑
        pass

# 任务创建：使用 hass.async_create_task()
self._connect_task = self.hass.async_create_task(self.async_ensure_connected())
```

### 2.5 错误处理

```python
# 捕获特定异常
try:
    await client.get_services()
except BleakNotFoundError as err:
    self._last_error = f"设备未找到: {err}"
    _LOGGER.error("Service discovery failed: %s", err)
except (BleakError, TimeoutError) as err:
    # 安全网
    self._last_error = f"连接失败: {err}"
    _LOGGER.exception("Unexpected error during connect")

# 记录到最后错误（供 UI 显示）
self._last_error: str | None = None
```

### 2.6 UUID 管理

```python
# 所有 UUID 定义在 const.py，全小写
UUID_NOTIFY_FFE1 = "0000ffe1-0000-1000-8000-00805f9b34fb"
UUID_BATTERY_LEVEL_2A19 = "00002a19-0000-1000-8000-00805f9b34fb"
UUID_ALERT_LEVEL_2A06 = "00002a06-0000-1000-8000-00805f9b34fb"

# 命名格式：UUID_<SERVICE>_<CHARACTERISTIC> 或 UUID_SERVICE_<HEX>
```

### 2.7 实体（Entity）模式

```python
class AntiLossTagBatterySensor(_AntiLossTagSensorBase):
    # 类属性配置
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, device: AntiLossTagDevice, entry: ConfigEntry) -> None:
        super().__init__(device, entry)
        self._attr_name = "Battery"  # 或中文名 "电量"
        self._attr_unique_id = f"{device.address}_battery"

    @property
    def native_value(self) -> int | None:
        return self._dev.battery
```

### 2.8 文档和注释

- **注释语言**：中文注释，英文变量/函数名
- **公开方法**：必须有 docstring（中文或英文）
- **常量分组**：使用注释分隔

```python
# ====== 多设备并发连接控制 ======
# 代码段
# ====== 结束 ======
```

---

## 3. Home Assistant 特定规范

### Config Flow

```python
class AntiLossTagConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_bluetooth(self, discovery_info) -> FlowResult:
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        return await self.async_step_confirm()

class OptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None) -> FlowResult:
        schema = vol.Schema({
            vol.Required(CONF_BATTERY_POLL_INTERVAL_MIN): vol.All(
                int, vol.Range(min=5, max=7 * 24 * 60)
            ),
        })
```

### DeviceInfo

```python
DeviceInfo(
    identifiers={(DOMAIN, self._dev.address)},  # 使用地址作为唯一标识
    name=self._dev.name,
    manufacturer="Unknown",
    model="BLE Anti-Loss Tag",
)
```

---

## 4. 架构模式

### 连接管理

- **全局连接槽位**：`BleConnectionManager` 使用 `asyncio.Semaphore` 限制并发
- **退避策略**：连接失败后指数退避（`2^n` 秒），避免连接风暴
- **锁使用**：`_connect_lock` 保护连接操作，`_gatt_lock` 保护读写

```python
# 获取槽位
acq = await self._conn_mgr.acquire(timeout=20.0)
if not acq.acquired:
    backoff = min(30, (2 ** self._connect_fail_count))
    return

# 失败释放
if self._conn_mgr is not None and self._conn_slot_acquired:
    await self._conn_mgr.release()
```

### 状态暴露

- 使用 `@property` 暴露只读状态
- 内部状态用 `_` 前缀
- 配置选项从 `entry.options` 读取

---

## 5. 禁止事项

 **不要**：
- 硬编码路径、地址、密钥
- 在循环中创建新 Task（应该复用或取消旧任务）
- 使用裸 `except:` 不记录日志
- 在 `@callback` 中使用阻塞操作
- 忘记更新 `manifest.json` 版本号

 **应该**：
- 所有文件以 `from __future__ import annotations` 开头
- 使用类型注解
- 错误时记录日志并更新 `self._last_error`
- 使用 `@callback` 标记非异步回调

---

## 6. 调试技巧

```bash
# 查看 Home Assistant 日志
tail -f ~/.homeassistant/home-assistant.log | grep anti_loss_tag

# 在 configuration.yaml 中启用调试
logger:
  default: info
  logs:
    custom_components.anti_loss_tag: debug
    bleak: debug
```

---

**最后更新**: 2025-02-08  
**参考文档**: `docs/技术文档/开发规范.md`（详细中文规范）
