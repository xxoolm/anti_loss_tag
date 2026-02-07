# BLE 防丢标签集成 - 详细整改修复方案

**制定日期**: 2025-02-08  
**方案类型**: 渐进式重构 + 代码归档（不删除文件）  
**预计工期**: 2-3 周（分阶段执行）

---

##  总体策略

### 核心原则

1. **不删除任何文件**：所有现有文件保留
2. **归档替代删除**：创建 `archived/` 目录存放旧代码
3. **渐进式迁移**：采用 Strangler Fig Pattern（绞杀者模式）
4. **向后兼容**：确保现有功能不受影响
5. **充分测试**：每个阶段都有验证点

### 架构决策

**基于网络搜索的最佳实践**：

1. **PEP 387 软弃用（Soft Deprecation）**
   - 标记为弃用，但不设置移除时间表
   - 在代码和文档中添加弃用警告
   - 允许旧代码继续工作，但新代码应避免使用

2. **Strangler Fig Pattern**
   - 逐步用新实现替换旧代码
   - 两套代码可以共存一段时间
   - 通过功能开关控制使用哪套实现

3. **Home Assistant 弃用政策**
   - 标准弃用周期：1 年
   - 在日志中显示弃用警告
   - 在文档中说明替代方案

---

## 阶段 1：代码归档和组织（第 1 周）

### 1.1 创建目录结构

```bash
# 创建归档目录
mkdir -p custom_components/anti_loss_tag/archived/
mkdir -p custom_components/anti_loss_tag/utils/
mkdir -p custom_components/anti_loss_tag/gatt_operations/
```

**新目录结构**：
```
custom_components/anti_loss_tag/
├── __init__.py                    # 主入口
├── manifest.json                  # 清单文件
├── const.py                       # 常量定义
├── config_flow.py                 # 配置流程
├── device.py                      # 主设备类（保留）
├── connection_manager.py          # 连接管理器（保留）
├── entity_mixin.py                # 实体混入类（保留）
├── sensor.py                      # 传感器实体（保留）
├── binary_sensor.py               # 二进制传感器（保留）
├── button.py                      # 按钮实体（保留）
├── switch.py                      # 开关实体（保留）
├── event.py                       # 事件实体（保留）
├── utils/                         # 工具函数（新建）
│   ├── __init__.py
│   ├── validation.py              # 输入验证
│   └── deprecation.py             # 弃用警告
├── gatt_operations/               # GATT 操作（新建）
│   ├── __init__.py
│   └── characteristic_cache.py    # 特征缓存
└── archived/                      # 归档目录（新建）
    ├── coordinator.py             # 旧的协调器
    ├── ble.py                     # 旧的 BLE 封装
    └── DEPRECATED.md              # 弃用说明
```

### 1.2 归档冗余代码

**步骤**：

```bash
# 移动文件到归档目录
git mv custom_components/anti_loss_tag/coordinator.py \
       custom_components/anti_loss_tag/archived/coordinator.py

git mv custom_components/anti_loss_tag/ble.py \
       custom_components/anti_loss_tag/archived/ble.py
```

**创建归档说明文件** (`archived/DEPRECATED.md`)：

```markdown
# 已归档模块说明

## 归档时间
2025-02-08

## 归档原因

这些模块是早期的 BLE 操作封装，功能已被 `device.py` 中的 `AntiLossTagDevice` 完全替代。

- `coordinator.py`: 实现了 `BleTagCoordinator`，使用 HA Coordinator 模式
- `ble.py`: 实现了 `BleTagBle`，提供了底层 GATT 操作封装

## 替代方案

所有功能已整合到 `device.py` 的 `AntiLossTagDevice` 类中：

- 设备连接管理 → `AntiLossTagDevice.async_ensure_connected()`
- GATT 读写操作 → `AntiLossTagDevice.async_read_battery()` 等
- 连接槽位管理 → `BleConnectionManager` (connection_manager.py)

## 弃用政策

根据 PEP 387 软弃用政策，这些代码将：
- 保留在 `archived/` 目录中
- 不再维护，但不会删除
- 不影响现有功能
- 可供历史参考

## 迁移指南

如果需要使用这些模块中的特定功能，请参考 `device.py` 中的实现。
```

### 1.3 更新导入引用

**检查是否有文件导入了归档的模块**：

```bash
grep -r "from .coordinator import" custom_components/anti_loss_tag/
grep -r "from .ble import" custom_components/anti_loss_tag/
grep -r "import coordinator" custom_components/anti_loss_tag/
grep -r "import ble" custom_components/anti_loss_tag/
```

**预期结果**：应该没有找到任何引用（根据之前的审查）

---

## 阶段 2：修复关键问题（第 1-2 周）

### 2.1 修复 CancelledError 处理

**问题位置**：`device.py:789`

**当前代码**：
```python
except asyncio.CancelledError:
    return
except (BleakError, TimeoutError, OSError) as err:
    self._last_error = f"电量轮询异常: {err}"
```

**修复方案**（基于 asyncio 最佳实践）：

```python
except asyncio.CancelledError:
    # 任务被取消，清理资源后重新抛出
    _LOGGER.debug("Battery loop cancelled for %s", self.address)
    raise  # 重新抛出，确保任务真正取消
except (BleakError, TimeoutError, OSError) as err:
    self._last_error = f"电量轮询异常: {err}"
    self._async_dispatch_update()
```

**理由**（来自网络搜索）：
- Python asyncio 文档明确指出：CancelledError 应该在清理后重新抛出
- 不重新抛出会导致任务无法正确取消
- 可能影响 `TaskGroup` 等结构化并发原语

### 2.2 添加 BLE 地址验证

**创建新文件** `utils/validation.py`：

```python
"""输入验证工具模块。"""

from __future__ import annotations

import re
import logging

_LOGGER = logging.getLogger(__name__)

# BLE 地址验证模式
# 支持 MAC 地址格式：XX:XX:XX:XX:XX:XX 或 XX-XX-XX-XX-XX-XX
# 支持匿名地址（较短）
MAC_ADDRESS_PATTERN = re.compile(
    r'^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$'
)
ANONYMOUS_ADDRESS_PATTERN = re.compile(
    r'^([0-9A-Fa-f]{2}[:-]){2}[0-9A-Fa-f]{2}$'
)


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
        if ord(char) < 32 and char not in (' ', '\t'):
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
    cleaned = address.replace(':', '').replace('-', '').upper()
    
    # 插入冒号分隔符
    return ':'.join(cleaned[i:i+2] for i in range(0, len(cleaned), 2))
```

**更新 `config_flow.py`** 添加验证：

```python
# 在文件开头添加导入
from .utils.validation import is_valid_ble_address, is_valid_device_name

# 在 async_step_user 方法中添加验证
async def async_step_user(self, user_input: dict | None = None) -> None:
    """Manual setup."""
    errors: dict[str, str] = {}

    if user_input is not None:
        address = user_input[CONF_ADDRESS].strip()
        
        # 验证 BLE 地址格式
        if not is_valid_ble_address(address):
            errors[CONF_ADDRESS] = "invalid_ble_address"
            schema = vol.Schema({
                vol.Required(CONF_ADDRESS): str,
                vol.Optional(CONF_NAME): str,
            })
            return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
        
        name = user_input.get(CONF_NAME, address).strip()
        
        # 验证设备名称
        if not is_valid_device_name(name):
            errors[CONF_NAME] = "invalid_device_name"
            schema = vol.Schema({
                vol.Required(CONF_ADDRESS): str,
                vol.Optional(CONF_NAME): str,
            })
            return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
        
        # 验证通过，继续原有逻辑
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()
        
        return self.async_create_entry(
            title=name,
            data={CONF_ADDRESS: address, CONF_NAME: name},
            options={
                CONF_ALARM_ON_DISCONNECT: DEFAULT_ALARM_ON_DISCONNECT,
                CONF_MAINTAIN_CONNECTION: DEFAULT_MAINTAIN_CONNECTION,
                CONF_AUTO_RECONNECT: DEFAULT_AUTO_RECONNECT,
                CONF_BATTERY_POLL_INTERVAL_MIN: DEFAULT_BATTERY_POLL_INTERVAL_MIN,
            },
        )
    
    schema = vol.Schema({
        vol.Required(CONF_ADDRESS): str,
        vol.Optional(CONF_NAME): str,
    })
    return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
```

**添加翻译字符串**（创建 `strings.json` 如果不存在）：

```json
{
  "config": {
    "step": {
      "user": {
        "data": {
          "address": "BLE 地址",
          "name": "设备名称（可选）"
        },
        "error": {
          "invalid_ble_address": "无效的 BLE 地址格式（应为 XX:XX:XX:XX:XX:XX）",
          "invalid_device_name": "设备名称不能为空且长度不能超过 248 字符"
        }
      }
    }
  }
}
```

### 2.3 改进 _on_disconnect 错误处理

**问题位置**：`device.py:356-368`

**当前代码**：
```python
def _on_disconnect(self, _client) -> None:
    self._connected = False
    self._cached_chars.clear()  # 如果抛异常？
    self._release_connection_slot_soon()
    self._client = None
    # ...
```

**修复方案**：

```python
def _on_disconnect(self, _client) -> None:
    """处理断开连接回调。
    
    注意：这是一个同步回调（来自 bleak），不能使用 await。
    所有清理操作都应该是非阻塞的。
    """
    try:
        self._connected = False
        # 清理特征缓存（如果失败，记录错误但继续清理）
        try:
            self._cached_chars.clear()
        except Exception as err:
            _LOGGER.error("Error clearing characteristic cache: %s", err)
    except Exception as err:
        _LOGGER.error("Error in disconnect callback: %s", err)
    finally:
        # 确保资源释放一定会执行
        self._release_connection_slot_soon()
        self._client = None
        self._alert_level_handle = None
        self._battery_level_handle = None
        self._async_dispatch_update()
```

**理由**：
- `_on_disconnect` 是 bleak 的回调，在后台线程执行
- 任何未捕获的异常都可能导致 bleak 崩溃
- 使用 try/finally 确保关键清理一定会执行

### 2.4 改进 _release_connection_slot_soon

**问题**：如果 `async_create_task` 失败，槽位可能泄漏

**修复方案**：

```python
def _release_connection_slot_soon(self) -> None:
    """从非异步回调上下文中释放连接槽位。"""
    if self._conn_mgr is not None and self._conn_slot_acquired:
        self._conn_slot_acquired = False
        # 添加错误处理，防止任务创建失败导致槽位泄漏
        try:
            task = self.hass.async_create_task(self._release_connection_slot())
            # 添加完成回调，捕获任务中的异常
            def _task_done(t: asyncio.Task) -> None:
                try:
                    t.exception()
                except Exception as err:
                    _LOGGER.error("Error in slot release task: %s", err)
            
            task.add_done_callback(_task_done)
        except Exception as err:
            _LOGGER.error("Failed to schedule slot release: %s", err)
            # 尝试同步释放（不推荐，但比泄漏好）
            try:
                # 注意：这可能在事件循环外执行，需要额外保护
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，创建任务
                    loop.create_task(self._release_connection_slot())
                else:
                    _LOGGER.warning("Event loop not running, slot may leak")
            except Exception as e:
                _LOGGER.error("Failed to release slot synchronously: %s", e)
```

---

## 阶段 3：代码质量改进（第 2 周）

### 3.1 提取魔法数字为常量

**创建新文件** `utils/constants.py`：

```python
"""常量定义模块。"""

from __future__ import annotations

# 电量轮询相关
BATTERY_POLL_JITTER_SECONDS = 30  # 抖动秒数
MIN_BATTERY_POLL_INTERVAL_MIN = 5  # 最小轮询间隔（分钟）
MAX_BATTERY_POLL_INTERVAL_MIN = 7 * 24 * 60  # 最大轮询间隔（7天，分钟）

# 连接退避相关
MIN_CONNECT_BACKOFF_SECONDS = 2  # 最小退避时间（秒）
MAX_CONNECT_BACKOFF_SECONDS = 60  # 最大退避时间（秒）
MAX_CONNECT_FAIL_COUNT = 6  # 最大失败计数（2^6 = 64秒）

# BLE 连接相关
DEFAULT_BLEAK_TIMEOUT = 20.0  # 默认 bleak 超时（秒）
CONNECTION_SLOT_ACQUIRE_TIMEOUT = 20.0  # 连接槽位获取超时（秒）

# 更新防抖动
ENTITY_UPDATE_DEBOUNCE_SECONDS = 1.0  # 实体更新防抖动时间（秒）

# GATT handle 范围
MIN_GATT_HANDLE = 0
MAX_GATT_HANDLE = 0xFFFF  # BLE handle 是 16 位
```

**更新 `device.py`** 使用常量：

```python
# 在文件开头添加导入
from .utils.constants import (
    BATTERY_POLL_JITTER_SECONDS,
    MIN_CONNECT_BACKOFF_SECONDS,
    MAX_CONNECT_BACKOFF_SECONDS,
    MAX_CONNECT_FAIL_COUNT,
    ENTITY_UPDATE_DEBOUNCE_SECONDS,
)

# 替换魔法数字
# 旧代码：jitter = random.randint(0, 30)
# 新代码：
jitter = random.randint(0, BATTERY_POLL_JITTER_SECONDS)

# 旧代码：backoff = min(30, (2 ** self._connect_fail_count))
# 新代码：
backoff = min(MAX_CONNECT_BACKOFF_SECONDS, (2 ** self._connect_fail_count))

# 旧代码：self._connect_fail_count = min(self._connect_fail_count + 1, 6)
# 新代码：
self._connect_fail_count = min(self._connect_fail_count + 1, MAX_CONNECT_FAIL_COUNT)
```

### 3.2 添加实体更新防抖动

**在 `device.py` 中添加防抖动逻辑**：

```python
# 在 __init__ 方法中添加
def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
    # ... 现有代码 ...
    
    # 防抖动相关
    self._update_debounce_handle: asyncio.TimerHandle | None = None

@callback
def _async_schedule_update(self) -> None:
    """调度更新（带防抖动）。"""
    # 取消之前的更新
    if self._update_debounce_handle is not None:
        self._update_debounce_handle.cancel()
    
    # 延迟调度新更新
    self._update_debounce_handle = self.hass.loop.call_later(
        ENTITY_UPDATE_DEBOUNCE_SECONDS,
        self._async_dispatch_update
    )

# 更新 _async_on_bluetooth_event 使用防抖动
@callback
def _async_on_bluetooth_event(
    self,
    service_info: bluetooth.BluetoothServiceInfoBleak,
    change: bluetooth.BluetoothChange,
) -> None:
    """Handle advertisement updates."""
    self._available = True
    self._rssi = service_info.rssi
    self._last_seen = datetime.now(timezone.utc)
    
    # 使用防抖动更新
    self._async_schedule_update()
    
    if self.maintain_connection and not self._connected:
        self._ensure_connect_task()
```

**理由**：
- BLE 广播频率可能很高（每秒几次）
- 每次广播都更新所有实体会导致 HA 性能问题
- 防抖动可以将多次快速更新合并为一次

### 3.3 改进输入验证和边界检查

**在 `utils/validation.py` 中添加**：

```python
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
```

**更新 `device.py` 使用验证函数**：

```python
# 在 _resolve_char_handle 中
try:
    handle = int(getattr(ch, "handle"))
    
    # 添加 handle 验证
    if not validate_gatt_handle(handle):
        _LOGGER.warning("Invalid GATT handle value: %d", handle)
        return None
    
    self._cached_chars[cu] = ch
    return handle
except (AttributeError, TypeError, ValueError):
    return None

# 在 async_read_battery 中
if data and len(data) >= 1:
    raw_level = int(data[0])
    level = validate_battery_level(raw_level)
    if level is not None:
        self._battery = level
        self._last_battery_read = datetime.now(timezone.utc)
        self._async_dispatch_update()
    else:
        _LOGGER.warning("Invalid battery level: %d", raw_level)
```

---

## 阶段 4：文档和测试（第 3 周）

### 4.1 更新文档

**创建 `MIGRATION_GUIDE.md`**：

```markdown
# 迁移指南

## 从旧版本迁移

如果你使用了 `coordinator.py` 或 `ble.py` 中的功能，这里是如何迁移到新 API 的指南。

## BleTagCoordinator 迁移

### 旧代码（archived/coordinator.py）
\`\`\`python
from .coordinator import BleTagCoordinator

coordinator = BleTagCoordinator(hass, entry)
await coordinator.async_start()
await coordinator.async_refresh_battery()
\`\`\`

### 新代码（device.py）
\`\`\`python
from .device import AntiLossTagDevice

device = AntiLossTagDevice(hass, entry)
device.async_start()
await device.async_read_battery(force_connect=True)
\`\`\`

## BleTagBle 迁移

### 旧代码（archived/ble.py）
\`\`\`python
from .ble import BleTagBle

ble = BleTagBle(hass, address)
await ble.write_alert_level(True)
battery = await ble.read_battery()
\`\`\`

### 新代码（device.py）
\`\`\`python
from .device import AntiLossTagDevice

device = AntiLossTagDevice(hass, entry)
await device.async_start_alarm()
# 电池通过 battery 属性访问
battery = device.battery
\`\`\`

## API 映射表

| 旧 API (coordinator.py) | 新 API (device.py) |
|------------------------|-------------------|
| `coordinator.async_refresh_battery()` | `device.async_read_battery()` |
| `coordinator.async_set_disconnect_alarm()` | `device.async_set_disconnect_alarm_policy()` |
| `coordinator.async_ring()` | `device.async_start_alarm()` + `async_stop_alarm()` |
| `coordinator.data.online` | `device.available` |
| `coordinator.data.battery` | `device.battery` |

| 旧 API (ble.py) | 新 API (device.py) |
|-----------------|-------------------|
| `ble.write_alert_level()` | `async_start_alarm()` / `async_stop_alarm()` |
| `ble.write_disconnect_alarm()` | `async_set_disconnect_alarm_policy()` |
| `ble.read_battery()` | `async_read_battery()` |

## 弃用政策

- 旧代码已移至 `archived/` 目录
- 不会立即删除，但不再维护
- 建议在新代码中使用新 API
- 旧 API 将在未来的版本中移除（至少提前 1 年通知）
```

**更新 `CHANGELOG.md`**（如果不存在则创建）：

```markdown
# 更新日志

## [Unreleased]

### Added
- BLE 地址格式验证
- 设备名称格式验证
- GATT handle 值验证
- 实体更新防抖动机制
- 输入验证工具模块 (`utils/validation.py`)
- 常量定义模块 (`utils/constants.py`)
- 特征缓存模块 (`gatt_operations/characteristic_cache.py`)

### Changed
- 改进 CancelledError 处理（确保任务正确取消）
- 改进 `_on_disconnect` 错误处理
- 改进连接槽位释放的可靠性
- 提取魔法数字为命名常量

### Fixed
- 电池轮询任务无法正确取消的问题
- 连接槽位可能泄漏的问题
- 断开连接回调中的异常处理

### Deprecated
- `coordinator.py` - 功能已整合到 `device.py`
- `ble.py` - 功能已整合到 `device.py`

### Migration
- 查看 `MIGRATION_GUIDE.md` 了解如何从旧 API 迁移

## [1.0.0] - 2025-02-08

### Added
- 初始版本
- BLE 防丢标签集成
- 支持电量监控、信号强度、按钮事件
- 远程控制（报警开关、防丢开关）
- 多设备并发连接管理
```

### 4.2 添加单元测试

**创建 `tests/` 目录和基础测试文件**：

```bash
mkdir -p tests
touch tests/__init__.py
touch tests/test_validation.py
touch tests/test_connection_manager.py
touch tests/test_device.py
```

**测试配置** (`tests/conftest.py`)：

```python
"""Pytest 配置。"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from homeassistant.core import HomeAssistant

@pytest.fixture
def hass():
    """创建 Home Assistant mock。"""
    hass = Mock(spec=HomeAssistant)
    hass.data = {}
    hass.loop = Mock()
    hass.async_create_task = Mock(return_value=Mock())
    return hass

@pytest.fixture
def config_entry():
    """创建配置条目 mock。"""
    entry = Mock()
    entry.data = {"address": "AA:BB:CC:DD:EE:FF", "name": "Test Tag"}
    entry.options = {
        "alarm_on_disconnect": False,
        "maintain_connection": True,
        "auto_reconnect": True,
        "battery_poll_interval_min": 360,
    }
    entry.runtime_data = None
    return entry
```

**验证模块测试** (`tests/test_validation.py`)：

```python
"""测试输入验证模块。"""

import pytest
from custom_components.anti_loss_tag.utils.validation import (
    is_valid_ble_address,
    is_valid_device_name,
    normalize_ble_address,
    validate_gatt_handle,
    validate_battery_level,
)

class TestBleAddressValidation:
    """测试 BLE 地址验证。"""
    
    def test_valid_mac_address_colon(self):
        """测试有效的 MAC 地址（冒号分隔）。"""
        assert is_valid_ble_address("AA:BB:CC:DD:EE:FF")
        assert is_valid_ble_address("aa:bb:cc:dd:ee:ff")
        assert is_valid_ble_address("00:11:22:33:44:55")
    
    def test_valid_mac_address_hyphen(self):
        """测试有效的 MAC 地址（连字符分隔）。"""
        assert is_valid_ble_address("AA-BB-CC-DD-EE-FF")
        assert is_valid_ble_address("aa-bb-cc-dd-ee-ff")
    
    def test_valid_anonymous_address(self):
        """测试有效的匿名地址。"""
        assert is_valid_ble_address("AA:BB:CC")
        assert is_valid_ble_address("aa-bb-cc")
    
    def test_invalid_addresses(self):
        """测试无效地址。"""
        assert not is_valid_ble_address("")
        assert not is_valid_ble_address("AA:BB:CC:DD:EE")
        assert not is_valid_ble_address("GG:HH:II:JJ:KK:LL")
        assert not is_valid_ble_address("AA:BB:CC:DD:EE:FF:GG")
        assert not is_valid_ble_address(None)
        assert not is_valid_ble_address(123)
    
    def test_normalize_address(self):
        """测试地址标准化。"""
        assert normalize_ble_address("aa:bb:cc:dd:ee:ff") == "AA:BB:CC:DD:EE:FF"
        assert normalize_ble_address("AA-BB-CC-DD-EE-FF") == "AA:BB:CC:DD:EE:FF"
        
        with pytest.raises(ValueError):
            normalize_ble_address("invalid")

class TestDeviceNameValidation:
    """测试设备名称验证。"""
    
    def test_valid_names(self):
        """测试有效名称。"""
        assert is_valid_device_name("Test Device")
        assert is_valid_device_name("标签A")
        assert is_valid_device_name("A")
        assert is_valid_device_name("  Test  ")  # 允许前后空格
    
    def test_invalid_names(self):
        """测试无效名称。"""
        assert not is_valid_device_name("")
        assert not is_valid_device_name("   ")
        assert not is_valid_device_name(None)
        assert not is_valid_device_name(123)

class TestGattHandleValidation:
    """测试 GATT handle 验证。"""
    
    def test_valid_handles(self):
        """测试有效 handle。"""
        assert validate_gatt_handle(0)
        assert validate_gatt_handle(0xFFFF)
        assert validate_gatt_handle(0x1234)
    
    def test_invalid_handles(self):
        """测试无效 handle。"""
        assert not validate_gatt_handle(-1)
        assert not validate_gatt_handle(0x10000)
        assert not validate_gatt_handle(None)

class TestBatteryLevelValidation:
    """测试电池电量验证。"""
    
    def test_valid_levels(self):
        """测试有效电量值。"""
        assert validate_battery_level(50) == 50
        assert validate_battery_level(0) == 0
        assert validate_battery_level(100) == 100
        assert validate_battery_level(150) == 100  # 限制上限
        assert validate_battery_level(-10) == 0    # 限制下限
    
    def test_invalid_levels(self):
        """测试无效电量值。"""
        assert validate_battery_level("abc") is None
        assert validate_battery_level(None) is None
```

**运行测试**：

```bash
# 安装测试依赖
pip install pytest pytest-asyncio pytest-cov

# 运行测试
pytest tests/ -v

# 运行测试并查看覆盖率
pytest tests/ --cov=custom_components/anti_loss_tag --cov-report=html
```

---

## 阶段 5：验证和部署（第 3 周）

### 5.1 本地测试清单

- [ ] 所有单元测试通过
- [ ] 手动测试 BLE 连接
- [ ] 测试配置流程（包括错误情况）
- [ ] �验所有实体（传感器、按钮、开关、事件）
- [ ] 测试错误恢复（设备断开、重连）
- [ ] 检查日志中的异常
- [ ] 验证性能（长时间运行稳定性）

### 5.2 Home Assistant 配置验证

```bash
# 在 Home Assistant 配置目录中运行
hass --script check_config --path ~/.homeassistant
```

### 5.3 部署步骤

1. **备份现有配置**
   ```bash
   cp -r ~/.homeassistant/custom_components/anti_loss_tag \
         ~/.homeassistant/custom_components/anti_loss_tag.backup
   ```

2. **部署新代码**
   ```bash
   cp -r custom_components/anti_loss_tag \
         ~/.homeassistant/custom_components/
   ```

3. **重启 Home Assistant**
   ```bash
   # 在 HA 中：配置 → 系统 → 服务器管理 → 重启
   ```

4. **验证安装**
   - 检查日志中是否有错误
   - 验证所有设备正常工作
   - 测试配置选项修改

---

## 风险评估和缓解

### 高风险项

1. **修改 CancelledError 处理**
   - 风险：可能影响任务取消行为
   - 缓解：充分测试，确保任务能正确取消
   - 回滚：如果出现问题，恢复旧代码

2. **添加输入验证**
   - 风险：可能拒绝原本有效的输入
   - 缓解：宽松验证，只拒绝明显无效的输入
   - 回滚：放宽验证规则

### 中风险项

1. **归档代码**
   - 风险：可能有未发现的依赖
   - 缓解：全局搜索确认无引用
   - 回滚：恢复文件到原位置

2. **添加防抖动**
   - 风险：可能延迟用户可见的更新
   - 缓解：防抖时间短（1 秒）
   - 回滚：移除防抖动逻辑

### 低风险项

1. 提取常量
2. 改进错误处理
3. 添加文档

---

## 时间估算

| 阶段 | 任务 | 预计时间 |
|------|------|---------|
| 1 | 代码归档和组织 | 2-3 天 |
| 2 | 修复关键问题 | 3-5 天 |
| 3 | 代码质量改进 | 3-5 天 |
| 4 | 文档和测试 | 3-5 天 |
| 5 | 验证和部署 | 2-3 天 |
| **总计** | | **13-21 天** |

---

## 成功标准

### 必须完成（P0）
- [ ] 不删除任何文件
- [ ] 归档冗余代码（coordinator.py, ble.py）
- [ ] 修复 CancelledError 处理
- [ ] 添加 BLE 地址验证
- [ ] 改进 _on_disconnect 错误处理
- [ ] 所有测试通过

### 应该完成（P1）
- [ ] 提取魔法数字为常量
- [ ] 添加实体更新防抖动
- [ ] 改进输入验证和边界检查
- [ ] 完善文档（迁移指南、更新日志）
- [ ] 添加基础单元测试

### 可以完成（P2）
- [ ] 重构长函数
- [ ] 添加更多测试
- [ ] 性能优化
- [ ] 统一代码风格

---

## 总结

本整改方案遵循以下原则：

1. **渐进式重构**：分阶段执行，每阶段都可以独立验证
2. **不删除代码**：归档替代删除，保持历史可追溯性
3. **向后兼容**：确保现有功能不受影响
4. **充分测试**：每个阶段都有明确的验证点
5. **文档完善**：提供迁移指南和更新日志

方案基于业界最佳实践（Strangler Fig Pattern、PEP 387 软弃用、asyncio 最佳实践），确保代码质量和可维护性。

---

**制定人**: AI 代码审查助手  
**参考文档**:  
- PEP 387: Backwards Compatibility Policy  
- Python asyncio 官方文档  
- Home Assistant 开发者文档  
- Strangler Fig Pattern (Martin Fowler)
