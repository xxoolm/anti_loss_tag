# 数据更新机制

本文档说明 anti_loss_tag 集成如何获取和更新设备数据。

## 目录

- [数据源](#数据源)
- [更新触发机制](#更新触发机制)
- [数据类型与更新频率](#数据类型与更新频率)
- [状态转换](#状态转换)
- [缓存机制](#缓存机制)
- [性能考虑](#性能考虑)

## 数据源

anti_loss_tag 集成从以下数据源获取信息：

### 1. 蓝牙广播（BLE Advertisement）

**数据内容**:
- 设备地址（MAC 地址）
- 设备名称
- RSSI（信号强度）
- 广播数据（包括设备状态等）

**获取方式**:
- 被动接收：Home Assistant 蓝牙集成自动扫描
- 更新频率：设备每次广播时（通常 100ms - 1s 间隔）

**用途**:
- 检测设备存在（在线状态）
- 更新 RSSI（信号强度）
- 获取部分设备状态（如报警状态）

**优势**:
- 无需连接，功耗低
- 实时性好

**限制**:
- 数据量有限
- 不可靠（可能丢包）

### 2. GATT 连接（主动读取）

**数据内容**:
- 电池电量
- 详细配置信息
- 其他特征数据

**获取方式**:
- 主动建立 GATT 连接
- 读取特征值
- 更新频率：按配置的轮询间隔（默认 6 小时）

**用途**:
- 读取电池电量
- 写入配置（如报警策略）
- 读取详细信息

**优势**:
- 数据完整可靠
- 可双向通信

**限制**:
- 需要保持连接
- 功耗较高
- 受并发连接数限制

## 更新触发机制

### 1. 实时更新（基于事件）

**触发条件**:
- 设备广播被接收到
- 设备连接状态变化
- 用户操作（按钮、开关）

**更新内容**:
- 在线状态
- 连接状态
- RSSI
- 按键事件

**更新频率**:
- 即时（广播到达时）

**示例**:
```python
async def _async_on_bluetooth_event(
    self,
    service_info: BluetoothServiceInfo,
    change: BluetoothChange,
) -> None:
    """处理蓝牙广播事件"""
    # 更新 RSSI
    self._rssi = service_info.advertisement.rssi
    
    # 更新在线状态
    self._update_availability(True)
    
    # 通知实体更新
    self.async_write_ha_state()
```

### 2. 定期轮询（基于时间）

**触发条件**:
- 达到配置的轮询间隔

**更新内容**:
- 电池电量

**更新频率**:
- 默认：6 小时
- 可配置范围：5 分钟 - 7 天

**实现**:
```python
async def _async_battery_loop(self) -> None:
    """后台电池轮询循环"""
    while True:
        try:
            # 读取电量
            battery = await self.async_read_battery()
            
            # 计算下次轮询时间（带抖动）
            interval = self.battery_poll_interval * 60
            jitter = random.randint(0, 30)  # 0-30秒抖动
            await asyncio.sleep(interval + jitter)
        except CancelledError:
            break
        except Exception:
            _LOGGER.exception("Battery poll failed")
```

### 3. 按需更新（用户操作）

**触发条件**:
- 用户点击按钮
- 用户切换开关

**更新内容**:
- 报警状态
- 断连报警策略

**更新频率**:
- 即时（操作时）

## 数据类型与更新频率

### 在线状态（Available）

**数据源**: 蓝牙广播

**更新触发**:
- 收到设备广播 → 在线
- 超时未收到广播 → 离线（默认 30 秒超时）

**更新频率**:
- 实时（每次广播）

**缓存**:
- 无缓存，直接反映广播状态

### 连接状态（Connected）

**数据源**: GATT 连接状态

**更新触发**:
- 连接成功 → 已连接
- 连接断开 → 已断开

**更新频率**:
- 实时（连接事件）

**缓存**:
- 存储在 `_connected` 属性

### 电池电量（Battery）

**数据源**: GATT 读取

**更新触发**:
- 定期轮询
- 用户手动刷新

**更新频率**:
- 默认：6 小时
- 最小：5 分钟

**缓存**:
- 缓存在 `_battery` 属性
- 缓存时间：`_last_battery_read`

**实现**:
```python
@property
def battery(self) -> int | None:
    """获取电池电量（带缓存）"""
    # 检查缓存是否有效（默认 6 小时）
    if self._last_battery_read and (time.time() - self._last_battery_read.timestamp()) < 21600:
        return self._battery
    return None
```

### RSSI（信号强度）

**数据源**: 蓝牙广播

**更新触发**:
- 每次收到广播

**更新频率**:
- 实时（广播间隔，通常 100ms - 1s）

**缓存**:
- 存储在 `_rssi` 属性
- 无过期时间

### 报警状态（Alarm State）

**数据源**:
- 广播数据（被动）
- GATT 写入（主动）

**更新触发**:
- 设备广播包含状态变化
- 用户操作

**更新频率**:
- 实时

**缓存**:
- 存储在 `_alarm_on` 属性

## 状态转换

### 在线状态转换

```
离线 (Available=False)
  ↓ 收到广播
在线 (Available=True)
  ↓ 超时 (30秒)
离线 (Available=False)
```

### 连接状态转换

```
未连接 (Connected=False)
  ↓ 需要操作 / maintain_connection=True
连接中 (Connecting)
  ↓ 连接成功
已连接 (Connected=True)
  ↓ 操作完成 / maintain_connection=False
断开中 (Disconnecting)
  ↓ 断开完成
未连接 (Connected=False)
```

## 缓存机制

### 电量缓存

**目的**: 减少 GATT 读取次数，降低功耗和干扰

**缓存策略**:
- 有效期：配置的轮询间隔
- 刷新：后台定期轮询
- 失效：超时后自动刷新

**读取逻辑**:
```python
async def async_read_battery(self, force_connect: bool = False) -> int:
    """读取电池电量"""
    # 如果未强制刷新且缓存有效，返回缓存值
    if not force_connect and self._battery_cache_valid():
        return self._battery
    
    # 否则执行实际读取
    battery = await self._read_battery_from_device()
    self._battery = battery
    self._last_battery_read = datetime.now()
    return battery
```

### 特征缓存

**目的**: 加速 GATT 操作，避免重复查找

**缓存内容**:
- UUID 到 handle 的映射
- 特征对象

**缓存策略**:
- 建立连接时缓存
- 连接断开时清空
- 多特征错误时重新获取

**实现**:
```python
self._cached_chars: dict[str, BleakGATTCharacteristic] = {}

async def _resolve_char_handle(self, uuid: str) -> int:
    """解析特征 handle（带缓存）"""
    if uuid in self._cached_chars:
        return self._cached_chars[uuid].handle
    
    # 查找特征并缓存
    char = await self._find_characteristic(uuid)
    self._cached_chars[uuid] = char
    return char.handle
```

## 性能考虑

### 1. 轮询频率选择

**低频（6 小时）**:
- 优点：省电，减少干扰
- 缺点：电量更新不及时

**高频（5 分钟）**:
- 优点：电量更新及时
- 缺点：耗电，可能影响设备性能

**建议**:
- 大部分场景使用默认值（6 小时）
- 需要监控电量时可设置为 1-2 小时
- 避免使用最小值（5 分钟），除非必要

### 2. 连接池管理

**全局连接槽位**:
- 默认：3 个并发连接
- 原因：平衡性能和稳定性

**槽位获取策略**:
- 先到先得
- 超时：20 秒
- 失败后指数退避

**影响**:
- 第 4 个设备需要等待槽位释放
- 长时间连接会占用槽位

### 3. 广播处理优化

**事件去重**:
- 避免重复处理相同的广播

**批量更新**:
- 合并多次更新为一次 HA 状态写入

**实现**:
```python
def async_write_ha_state(self) -> None:
    """通知 Home Assistant 更新实体状态"""
    # 使用 asyncio.Event 避免频繁更新
    if not self._update_pending:
        self._update_pending = True
        self.hass.async_create_task(self._async_update_entities())
```

## 数据一致性保证

### 1. 乐观更新

**策略**: 先更新本地状态，再更新 Home Assistant

**优势**:
- 响应快速
- 减少阻塞

**示例**:
```python
# 1. 立即更新本地状态
self._battery = new_battery

# 2. 异步通知 HA
self.async_write_ha_state()
```

### 2. 最终一致性

**保证**: 状态最终会一致

**场景**:
- 短暂的不一致是允许的
- 下次更新会修正

### 3. 错误恢复

**策略**: 错误时保持旧状态，记录错误

**实现**:
```python
try:
    new_value = await read_from_device()
    self._state = new_value
except Exception as err:
    _LOGGER.error("Read failed: %s", err)
    self._last_error = str(err)
    # 保持旧状态
```

## 调试数据更新

### 启用详细日志

```yaml
logger:
  default: info
  logs:
    custom_components.anti_loss_tag: debug
```

### 关键日志消息

**数据更新**:
```
DEBUG custom_components.anti_loss_tag: Updated RSSI: -45
DEBUG custom_components.anti_loss_tag: Updated battery: 85%
```

**状态转换**:
```
INFO custom_components.anti_loss_tag: Device available=True
INFO custom_components.anti_loss_tag: Connected to AA:BB:CC:DD:EE:FF
```

**错误**:
```
ERROR custom_components.anti_loss_tag: Failed to read battery: <error>
```

## 相关文档

- [已知限制](KNOWN_LIMITATIONS.md)
- [故障排查指南](TROUBLESHOOTING.md)
- [集成配置](README.md)
