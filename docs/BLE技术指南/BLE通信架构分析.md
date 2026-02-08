# BLE设备通信架构分析

**文档版本**: v2.0  
**制定日期**: 2025-02-08  
**技术标准**: Bluetooth Core Specification 5.1  
**适用范围**: BLE防丢标签设备通信

---

## 1. BLE通信架构概述

### 1.1 通信模型

本集成采用标准BLE GATT（Generic Attribute Profile）通信模型：

```
Home Assistant (Central)
    ↓ BLE连接
KT6368A设备 (Peripheral)
    ↓ GATT服务
FFE0服务 (Anti-loss Tag)
    ├── FFE1特征 (Notify)
    └── FFE2特征 (Write)
```

### 1.2 角色定义

- **Central（中心设备）**: Home Assistant运行设备（如树莓派）
- **Peripheral（外围设备）**: KT6368A防丢标签
- **GATT Client**: Home Assistant集成
- **GATT Server**: KT6368A设备固件

---

## 2. 异步编程模式

### 2.1 Python asyncio架构

基于Python 3.11+的asyncio实现异步事件循环：

```python
import asyncio
from bleak import BleakClient

class BLEDeviceManager:
    """BLE设备管理器"""
    
    def __init__(self):
        self._connection_lock = asyncio.Lock()
        self._gatt_lock = asyncio.Lock()
        self._reconnect_task: asyncio.Task | None = None
    
    async def connect(self, address: str) -> None:
        """异步连接"""
        async with self._connection_lock:
            # 连接逻辑
            pass
```

### 2.2 事件驱动设计

使用回调模式处理BLE通知：

```python
def _notification_handler(self, sender: int, data: bytearray) -> None:
    """BLE通知回调"""
    try:
        # 解析数据
        event_type = data[0]
        payload = data[1:-1]
        
        # 触发事件
        self.hass.bus.async_fire(
            f"{DOMAIN}_event",
            {
                "device_id": self._address,
                "event_type": event_type,
                "data": payload.hex()
            }
        )
    except Exception as e:
        _LOGGER.error("通知处理错误: %s", e)
```

---

## 3. 状态机设计

### 3.1 连接状态管理

设备连接采用状态机模式：

```
DISCONNECTED → CONNECTING → CONNECTED → DISCONNECTING → DISCONNECTED
                    ↓              ↓
                   FAILED          RECONNECTING
```

### 3.2 状态转换

```python
class ConnectionState(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    FAILED = "failed"
    RECONNECTING = "reconnecting"

class BLEDevice:
    def __init__(self):
        self._state = ConnectionState.DISCONNECTED
        self._state_lock = asyncio.Lock()
    
    async def _transition_to(self, new_state: ConnectionState) -> None:
        """状态转换"""
        async with self._state_lock:
            old_state = self._state
            self._state = new_state
            _LOGGER.debug("状态: %s → %s", old_state, new_state)
```

---

## 4. 错误处理策略

### 4.1 连接错误分类

| 错误类型 | 处理策略 | 重试机制 |
|---------|---------|---------|
| 设备未找到 | 立即重试3次 | 指数退避 |
| 连接超时 | 延迟重试 | 2^n 秒 |
| GATT错误 | 断开重连 | 清除缓存 |
| 服务不可用 | 记录错误 | 停止连接 |

### 4.2 重连策略

```python
async def _reconnect_loop(self) -> None:
    """重连循环"""
    backoff = 1
    
    while self._should_reconnect:
        try:
            await asyncio.sleep(backoff)
            await self._connect_internal()
            backoff = 1  # 成功后重置
        except Exception as e:
            backoff = min(backoff * 2, 60)  # 最大60秒
            _LOGGER.warning("重连失败: %s, %d秒后重试", e, backoff)
```

---

## 5. 性能优化

### 5.1 连接池管理

使用信号量限制并发连接：

```python
class BleConnectionManager:
    """BLE连接管理器"""
    
    _connection_semaphore = asyncio.Semaphore(3)  # 最多3个并发连接
    
    @classmethod
    async def acquire_slot(cls, timeout: float = 20.0) -> bool:
        """获取连接槽位"""
        try:
            await asyncio.wait_for(
                cls._connection_semaphore.acquire(),
                timeout=timeout
            )
            return True
        except asyncio.TimeoutError:
            return False
```

### 5.2 操作锁机制

使用双重锁保护关键操作：

```python
async def write_gatt_char(self, uuid: str, data: bytes) -> None:
    """GATT写入操作"""
    async with self._gatt_lock:  # 保护GATT操作
        if not self._connected:
            raise BleakError("设备未连接")
        
        await self._client.write_gatt_char(uuid, data)
```

---

## 6. 数据协议

### 6.1 命令格式

基于KT6368A芯片规格定义数据包格式：

```
[Byte 0][Byte 1...N-2][Byte N-1]
[CMD  ][DATA        ][CHECKSUM]
```

**示例**: 发送报警距离设置

```python
def _build_command(self, cmd: int, data: bytes) -> bytes:
    """构建命令包"""
    packet = bytes([cmd]) + data
    checksum = sum(packet) & 0xFF
    return packet + bytes([checksum])

# 设置距离为3米
cmd_packet = _build_command(0x01, bytes([0x03]))
# 结果: 01 03 04
```

### 6.2 响应解析

```python
def _parse_response(self, data: bytes) -> dict:
    """解析响应数据"""
    if len(data) < 2:
        raise ValueError("数据包太短")
    
    cmd = data[0]
    payload = data[1:-1]
    checksum = data[-1]
    
    # 验证校验和
    if checksum != (sum(data[:-1]) & 0xFF):
        raise ValueError("校验和错误")
    
    return {
        "command": cmd,
        "payload": payload,
        "valid": True
    }
```

---

## 7. 最佳实践

### 7.1 连接管理

1. **及时释放资源**: 使用`async with`确保资源释放
2. **避免频繁重连**: 使用指数退避策略
3. **状态同步**: 使用锁保护共享状态
4. **错误日志**: 记录所有错误以便诊断

### 7.2 性能优化

1. **并发控制**: 使用信号量限制并发连接
2. **操作批处理**: 合并多个GATT操作
3. **缓存服务信息**: 避免重复发现服务
4. **异步优先**: 所有I/O操作使用异步

### 7.3 安全考虑

1. **输入验证**: 验证所有输入数据
2. **错误处理**: 捕获所有可能的异常
3. **资源限制**: 设置超时和重试次数
4. **日志脱敏**: 不记录敏感数据

---

## 8. 完整示例

### 8.1 设备类实现

```python
import asyncio
from bleak import BleakClient
from enum import Enum

class ConnectionState(Enum):
    """连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"

class AntiLossTagDevice:
    """防丢标签设备"""
    
    def __init__(self, address: str, hass):
        self._address = address
        self._hass = hass
        self._client = None
        self._state = ConnectionState.DISCONNECTED
        self._lock = asyncio.Lock()
    
    async def connect(self) -> None:
        """连接设备"""
        async with self._lock:
            if self._state != ConnectionState.DISCONNECTED:
                return
            
            self._state = ConnectionState.CONNECTING
            try:
                self._client = BleakClient(self._address)
                await self._client.connect()
                self._state = ConnectionState.CONNECTED
            except Exception as e:
                self._state = ConnectionState.DISCONNECTED
                raise
    
    async def disconnect(self) -> None:
        """断开连接"""
        async with self._lock:
            if self._client:
                await self._client.disconnect()
                self._client = None
            self._state = ConnectionState.DISCONNECTED
    
    @property
    def connected(self) -> bool:
        """是否已连接"""
        return self._state == ConnectionState.CONNECTED
```

### 8.2 使用示例

```python
async def main():
    """主函数"""
    device = AntiLossTagDevice("AA:BB:CC:DD:EE:FF", hass)
    
    try:
        # 连接
        await device.connect()
        print(f"已连接: {device.connected}")
        
        # 操作设备
        # ...
        
    finally:
        # 断开连接
        await device.disconnect()

asyncio.run(main())
```

---

## 9. 故障排除

### 9.1 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 设备找不到 | 设备未开启或距离太远 | 确保设备在附近并开启 |
| 连接失败 | 设备已连接到其他中心 | 断开其他连接 |
| 服务不可用 | 设备固件问题 | 重启设备 |
| 通知无响应 | 未开启通知 | 调用start_notify |

### 9.2 调试技巧

```python
# 启用bleak调试日志
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('bleak').setLevel(logging.DEBUG)

# 使用BLE抓包工具验证
# - Linux: btmon
# - Windows: Ellipal BLE Sniffer
# - macOS: Xcode Bluetooth Tools
```

---

## 10. 参考资料

- [Bluetooth Core Specification 5.1](https://www.bluetooth.com/specifications/bluetooth-core-specification/)
- [bleak库文档](https://bleak.readthedocs.io/)
- [Python asyncio文档](https://docs.python.org/3/library/asyncio.html)
- [KT6368A芯片数据手册](./KT6368A固件文档.md)

---

**文档状态**: 已完成  
**最后更新**: 2025-02-08  
**适用版本**: v1.6.0+
