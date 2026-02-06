# OpenCode Agent 协作执行手册

## 0. 项目概述

**项目类型**: Home Assistant 自定义集成 (BLE 防丢标签)  
**技术栈**: Python 3.11+, Home Assistant Core API, bleak (BLE 库)  
**代码结构**: `anti_loss_tag_v1/` 和 `anti_loss_tag_v2/` 两个版本，结构相同

## 1. 构建与测试命令

 **重要**: 此项目当前**没有自动化测试**或 lint 配置。

### 本地开发（无需构建）
```bash
# 此集成通过 Home Assistant 加载，无需独立构建
# 开发时将代码复制到 Home Assistant 的 custom_components 目录
cp -r anti_loss_tag_v1 ~/.homeassistant/custom_components/anti_loss_tag
```

### 代码风格检查（建议）
```bash
# 建议添加以下配置文件（当前不存在）：
# - pyproject.toml (配置 ruff, mypy)
# - requirements.txt 或 requirements_dev.txt

# 手动检查建议：
ruff check anti_loss_tag_v1/ anti_loss_tag_v2/
mypy anti_loss_tag_v1/ anti_loss_tag_v2/
```

### 单个测试文件执行（未来）
```bash
# 当前无测试。如需添加测试，应创建 tests/ 目录并使用 pytest
pytest tests/test_device.py -v
pytest tests/test_sensor.py -v
```

### Home Assistant 验证
```bash
# 在 Home Assistant 配置目录中检查配置
hass --script check_config
```

## 2. 代码风格规范

### 2.1 导入顺序（严格遵循）
```python
from __future__ import annotations  # 第一行（所有文件必须有）

# 标准库
import asyncio
import logging
from collections.abc import Callable

# 第三方库
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from bleak.exc import BleakError

# 本地模块
from .const import DOMAIN, CONF_ADDRESS
from .device import AntiLossTagDevice
```

### 2.2 类型注解（必须）
- **所有函数**必须有返回类型注解
- 使用 `|` 语法（PEP 604）表示可选类型：`int | None`
- 集合类型使用内置泛型：`list[str]`、`dict[str, int]`、`set[Callable[[], None]]`
- 回调函数类型：`Callable[[], None]`、`Callable[[ButtonEvent], None]`

```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """函数必须有 docstring 和类型注解。"""
    pass

def _opt_int(self, key: str, default: int) -> int:
    """私有方法也需要类型注解。"""
    pass
```

### 2.3 命名约定
- **类名**: PascalCase (例: `AntiLossTagDevice`, `OptionsFlowHandler`)
- **函数/方法**: snake_case (例: `async_setup_entry`, `_async_write_bytes`)
- **私有成员**: 前缀下划线 (例: `_client`, `_connected`, `_ensure_connect_task`)
- **常量**: UPPER_SNAKE_CASE (例: `DOMAIN`, `CONF_ADDRESS`, `UUID_NOTIFY_FFE1`)
- **属性**: 使用 `@property` 装饰器，无下划线前缀 (例: `available`, `connected`)

### 2.4 异步编程规范
- **所有 Home Assistant 相关方法**必须是 `async def`
- **回调函数**使用 `@callback` 装饰器，不使用 `async def`
- **锁**: 使用 `asyncio.Lock` 保护共享状态，避免竞态条件
- **任务创建**: 使用 `hass.async_create_task()` 而非 `asyncio.create_task()`

```python
async def async_ensure_connected(self) -> None:
    """连接方法必须使用 async def。"""
    async with self._connect_lock:  # 使用锁保护
        # 连接逻辑
        pass

@callback
def _async_on_bluetooth_event(self, service_info, change) -> None:
    """回调函数使用 @callback，不能是 async。"""
    self._available = True
```

### 2.5 错误处理
- **特定异常优先**: 捕获具体异常类型（`BleakError`, `BleakConnectionError`）而非裸 `Exception`
- **安全网**: 最外层可使用 `except Exception as err` 作为安全网，记录后返回
- **错误状态**: 使用 `self._last_error: str | None` 记录错误，供 UI 显示
- **日志**: 使用 `_LOGGER` 模块级常量，级别适当（debug/info/warning/error）

```python
try:
    await client.get_services()
except (BleakError, BleakNotFoundError) as err:
    self._last_error = f"连接失败: {err}"
    _LOGGER.error("Service discovery failed: %s", err)
except Exception as err:  # 安全网
    self._last_error = f"未知错误: {err}"
    _LOGGER.exception("Unexpected error")
```

### 2.6 数据类使用
- **简单数据容器**: 使用 `@dataclass`（例: `ButtonEvent`）
- **有状态对象**: 使用普通类（例: `AntiLossTagDevice`, `BleConnectionManager`）

```python
@dataclass
class ButtonEvent:
    when: datetime
    raw: bytes
```

### 2.7 属性访问模式
- **只读状态**: 使用 `@property`，不提供 setter（例: `available`, `rssi`）
- **配置选项**: 使用 `@property` 读取 `entry.options`（例: `maintain_connection`）
- **内部状态**: 前置下划线（`_connected`, `_battery`），通过属性暴露

### 2.8 文档字符串
- **所有公开方法**必须有 docstring
- **中文注释**: 代码注释使用中文，但变量名/函数名保持英文
- **常量分组**: 按功能分组，使用注释分隔

```python
# ====== 多设备并发连接控制（全局连接槽位 + 退避） ======
# 代码段
# ====== 结束 ======
```

### 2.9 UUID 管理
- **所有 BLE UUID**定义在 `const.py` 中
- **UUID 全小写**，即使标准是混合大小写
- **命名**: `UUID_<SERVICE>_<CHARACTERISTIC>` 或 `UUID_SERVICE_<HEX>`

```python
UUID_NOTIFY_FFE1 = "0000ffe1-0000-1000-8000-00805f9b34fb"
UUID_BATTERY_LEVEL_2A19 = "00002a19-0000-1000-8000-00805f9b34fb"
```

## 3. Home Assistant 集成特定规范

### 3.1 平台设置
- **PLATFORMS**: 在 `__init__.py` 定义，使用 `Platform` 枚举
- **entity_id 命名**: `{device.address}_{entity_type}` (例: `AA:BB:CC:DD:EE:FF_battery`)
- **实体名称**: 使用中文，格式 `{device.name} {类型}` (例: `标签A 电量`)

### 3.2 Config Flow
- **继承**: `config_entries.ConfigFlow`, domain=DOMAIN
- **步骤方法**: `async_step_bluetooth`, `async_step_user`, `async_step_confirm`
- **Options Flow**: 单步骤，所有选项在 `async_step_init` 中定义
- **Schema**: 使用 `voluptuous`, 设置合理的默认值和范围

```python
vol.Required(
    CONF_BATTERY_POLL_INTERVAL_MIN,
    default=opts.get(CONF_BATTERY_POLL_INTERVAL_MIN, DEFAULT_BATTERY_POLL_INTERVAL_MIN),
): vol.All(int, vol.Range(min=5, max=7 * 24 * 60)),
```

### 3.3 设备信息
- **DeviceInfo**: 使用设备地址作为唯一标识符
- **制造商/型号**: 使用中文，例如 `manufacturer="未知"`, `model="BLE 防丢标签"`

```python
DeviceInfo(
    identifiers={(DOMAIN, self._dev.address)},
    name=self._dev.name,
    manufacturer="未知",
    model="BLE 防丢标签",
)
```

## 4. 调试与日志

### 日志级别
- **DEBUG**: 详细的 BLE 操作细节（GATT 句柄解析、通知处理）
- **INFO**: 重要的状态变化（连接成功、断开、配置更新）
- **WARNING**: 警告但不影响功能的异常（多个 UUID 特征匹配）
- **ERROR**: 操作失败但仍可恢复（连接失败、读取失败）

### 错误追踪
- **最后错误**: 始终记录到 `self._last_error`，供实体 UI 显示
- **日志上下文**: 使用 `%s` 占位符，而非字符串拼接

```python
_LOGGER.error("Failed to read battery from %s: %s", self.address, err)
```

## 5. 并发控制

### 连接槽位管理
- **全局管理器**: `BleConnectionManager` 使用 `asyncio.Semaphore` 限制并发连接数
- **槽位获取**: 连接前 `acquire()`, 失败后必须 `release()`
- **退避策略**: 连接失败后指数退避（`2^n` 秒），避免连接风暴

```python
# 获取槽位
acq = await self._conn_mgr.acquire(timeout=20.0)
if not acq.acquired:
    # 退避
    backoff = min(30, (2 ** self._connect_fail_count))
    self._cooldown_until_ts = time.time() + backoff
    return

# 失败释放
if self._conn_mgr is not None and self._conn_slot_acquired:
    await self._conn_mgr.release()
    self._conn_slot_acquired = False
```

### 锁的使用
- **连接锁**: `_connect_lock` 保护连接/断开操作
- **GATT 锁**: `_gatt_lock` 保护读写操作

## 6. 版本管理

- **当前版本**: v1 和 v2 结构相同，v2 可能是未来改进版
- **修改代码时**: 同时更新两个版本，除非明确知道差异
- **manifest.json**: 记录版本号和依赖

## 7. 禁止事项

 **不要**：
- 硬编码中文路径或绝对路径
- 在循环中创建新的 asyncio.Task（应该复用或取消旧任务）
- 使用裸 `except:` 不记录日志
- 修改后忘记更新 `manifest.json` 版本号
- 在回调函数中使用阻塞操作

 **应该**：
- 所有文件以 `from __future__ import annotations` 开头
- 使用类型注解提高代码可读性
- 错误处理时记录日志并更新 `self._last_error`
- 修改代码后检查中文字符串是否正确显示
- 使用 `@callback` 标记非异步回调

## 8. 常见任务模式

### 添加新的传感器实体
1. 在 `sensor.py` 创建新类，继承 `_AntiLossTagSensorBase`
2. 设置类属性（`_attr_device_class`, `_attr_native_unit_of_measurement`）
3. 实现 `native_value` 属性
4. 在 `async_setup_entry` 中添加到 `async_add_entities`

### 添加新的配置选项
1. 在 `const.py` 定义 `CONF_*` 和 `DEFAULT_*`
2. 在 `OptionsFlowHandler.async_step_init` 添加 schema
3. 在 `device.py` 添加 `@property` 方法读取选项
4. 在 `async_apply_entry_options` 中处理选项变更

### 处理新的 BLE 特征
1. 在 `const.py` 添加 UUID 常量
2. 在 `device.py` 添加读写方法（参考 `async_read_battery`）
3. 使用 `_resolve_char_handle` 解决 UUID 冲突
4. 使用 `@property` 暴露读取结果

---

**最后更新**: 2025-02-06  
**适用于**: anti_loss_tag_v1, anti_loss_tag_v2
