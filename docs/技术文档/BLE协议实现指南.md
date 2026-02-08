# BLE协议实现指南

**文档版本**: v1.0  
**适用芯片**: KT6368A 双模蓝牙5.1 SoC  
**协议规范**: Bluetooth Core Specification 5.1  
**实现语言**: Python 3.11+  

---

## 目录

1. [BLE GATT协议概述](#1-ble-gatt协议概述)
2. [KT6368A芯片特性](#2-kt6368a芯片特性)
3. [服务和特征定义](#3-服务和特征定义)
4. [连接管理](#4-连接管理)
5. [数据传输协议](#5-数据传输协议)
6. [Python异步编程模式](#6-python异步编程模式)
7. [bleak库使用指南](#7-bleak库使用指南)
8. [错误处理与重连策略](#8-错误处理与重连策略)
9. [性能优化技巧](#9-性能优化技巧)
10. [完整代码示例](#10-完整代码示例)

---

## 1. BLE GATT协议概述

### 1.1 GATT架构

GATT（Generic Attribute Profile）是BLE的核心配置文件，定义了设备间数据交换的通用方式。

**基本概念**：
- **Profile**: 设备功能的集合
- **Service**: 服务的逻辑单元
- **Characteristic**: 数据项，包含值和描述
- **Descriptor**: 特征的描述信息

**层级结构**：
```
Profile (设备配置文件)
  └── Service (服务)
      ├── Characteristic (特征)
      │   ├── Value (值)
      │   └── Descriptor (描述符)
      └── ...
```

### 1.2 GATT操作

**标准GATT操作**：
- **Read**: 读取特征值
- **Write**: 写入特征值
- **Notify**: 主动通知数据变化
- **Indicate**: 带确认的通知

**操作流程**：
```
1. 设备发现 → 扫描周围BLE设备
2. 连接建立 → 创建GATT连接
3. 服务发现 → 获取服务列表
4. 特征发现 → 获取特征列表
5. 读写操作 → 数据交换
6. 断开连接 → 释放资源
```

---

## 2. KT6368A芯片特性

### 2.1 芯片规格

**基本信息**：
- **型号**: KT6368A
- **封装**: SOP-8
- **蓝牙版本**: 5.1双模
- **工作频率**: 2.4GHz ISM频段
- **发射功率**: 可调（最高+10dBm）
- **接收灵敏度**: -94dBm

**主要功能**：
- BLE peripheral和central角色
- 支持多连接
- 低功耗模式
- OTA升级

### 2.2 防丢标签特性

**FFE0服务**（主服务）：
- UUID: `0000FFE0-0000-1000-8000-00805F9B34FB`
- 用途: 防丢标签主服务

**FFE1特征**（通知）：
- UUID: `0000FFE1-0000-1000-8000-00805F9B34FB`
- 属性: Notify
- 用途: 按钮事件通知、状态变化

**FFE2特征**（写入）：
- UUID: `0000FFE2-0000-1000-8000-00805F9B34FB`
- 属性: Write | WriteWithoutResponse
- 用途: 报警控制、距离配置、静音设置

---

## 3. 服务和特征定义

### 3.1 服务发现

**服务发现流程**：
```python
async def discover_services(client):
    """发现所有服务"""
    services = client.services
    
    for service in services:
        _LOGGER.info(f"发现服务: {service.uuid}")
        
        for char in service.characteristics:
            _LOGGER.info(f"  特征: {char.uuid}")
            _LOGGER.info(f"    属性: {char.properties}")
```

### 3.2 FFE0服务定义

**服务UUID**: `0000FFE0-0000-1000-8000-00805F9B34FB`

**包含特征**：
1. **FFE1** - 通知特征
2. **FFE2** - 写入特征

**代码示例**：
```python
SERVICE_UUID = "0000FFE0-0000-1000-8000-00805F9B34FB"
CHAR_NOTIFY_UUID = "0000FFE1-0000-1000-8000-00805F9B34FB"
CHAR_WRITE_UUID = "0000FFE2-0000-1000-8000-00805F9B34FB"

async def setup_ffeo_service(client):
    """设置FFE0服务"""
    service = client.services.get_service(SERVICE_UUID)
    
    if not service:
        raise ValueError("FFE0服务未发现")
    
    # 获取特征
    char_notify = service.get_characteristic(CHAR_NOTIFY_UUID)
    char_write = service.get_characteristic(CHAR_WRITE_UUID)
    
    return char_notify, char_write
```

### 3.3 特征操作

**FFE1 - 通知订阅**：
```python
async def subscribe_notify(client, char_notify):
    """订阅通知"""
    def notification_handler(sender, data):
        _LOGGER.info(f"收到通知: {data.hex()}")
    
    await client.start_notify(char_notify, notification_handler)
```

**FFE2 - 数据写入**：
```python
async def write_control(client, char_write, data):
    """写入控制数据"""
    await client.write_gatt_char(char_write, data)
```

---

## 4. 连接管理

### 4.1 连接建立

**异步连接**：
```python
import asyncio
from bleak import BleakClient

async def connect_device(address: str):
    """连接BLE设备"""
    async with BleakClient(address) as client:
        _LOGGER.info(f"已连接: {address}")
        
        # 检查连接状态
        if client.is_connected:
            _LOGGER.info("连接成功")
            
            # 服务发现
            services = await client.get_services()
            _LOGGER.info(f"发现服务数: {len(services)}")
```

### 4.2 连接池管理

**使用信号量限制并发连接**：
```python
import asyncio

class BleConnectionManager:
    def __init__(self, max_connections: int = 3):
        self._semaphore = asyncio.Semaphore(max_connections)
        self._connections: dict[str, BleakClient] = {}
    
    async def connect(self, address: str) -> BleakClient:
        """连接设备（带并发限制）"""
        async with self._semaphore:
            if address in self._connections:
                return self._connections[address]
            
            client = BleakClient(address)
            await client.connect()
            
            self._connections[address] = client
            return client
    
    async def disconnect(self, address: str):
        """断开连接"""
        if address in self._connections:
            await self._connections[address].disconnect()
            del self._connections[address]
```

### 4.3 连接状态监控

**监控连接状态**：
```python
async def monitor_connection(client):
    """监控连接状态"""
    while True:
        if not client.is_connected:
            _LOGGER.warning("连接已断开")
            break
        
        await asyncio.sleep(1)
```

---

## 5. 数据传输协议

### 5.1 FFE1通知数据格式

**按钮事件通知**：
```
字节0: 事件类型
  - 0x01: 单击
  - 0x02: 双击
  - 0x03: 长按
字节1-7: 保留
```

**状态变化通知**：
```
字节0: 状态类型
  - 0x10: 连接状态
  - 0x11: 电池状态
字节1: 状态值
字节2-7: 保留
```

### 5.2 FFE2写入数据格式

**报警控制**：
```
字节0: 命令类型 (0xA0)
字节1: 报警开关
  - 0x00: 关闭报警
  - 0x01: 开启报警
字节2: 报警距离 (0-10)
  - 0: 近距离 (1-2米)
  - 5: 中距离 (5-10米)
  - 10: 远距离 (15-20米)
字节3: 报警类型
  - 0x00: 声音+振动
  - 0x01: 仅声音
  - 0x02: 仅振动
字节4-7: 保留
```

**静音设置**：
```
字节0: 命令类型 (0xA1)
字节1: 静音时长 (秒)
字节2-7: 保留
```

### 5.3 数据封装

**命令封装函数**：
```python
def build_alarm_command(
    enable: bool,
    distance: int,
    alarm_type: int = 0x00
) -> bytes:
    """构建报警控制命令"""
    return bytes([
        0xA0,              # 命令类型
        0x01 if enable else 0x00,  # 开关
        distance,          # 距离
        alarm_type,        # 报警类型
        0x00, 0x00, 0x00, 0x00  # 保留
    ])

def build_mute_command(duration: int) -> bytes:
    """构建静音命令"""
    return bytes([
        0xA1,              # 命令类型
        duration,          # 静音时长
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00  # 保留
    ])
```

---

## 6. Python异步编程模式

### 6.1 asyncio基础

**事件循环**：
```python
import asyncio

async def main():
    """主函数"""
    # 创建任务
    task1 = asyncio.create_task(device_scan())
    task2 = asyncio.create_task(device_monitor())
    
    # 等待任务完成
    await asyncio.gather(task1, task2)

if __name__ == "__main__":
    asyncio.run(main())
```

### 6.2 异步上下文管理器

**资源自动管理**：
```python
class BleConnection:
    def __init__(self, address: str):
        self.address = address
        self.client = None
    
    async def __aenter__(self):
        """进入上下文"""
        self.client = BleakClient(self.address)
        await self.client.connect()
        return self.client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if self.client:
            await self.client.disconnect()

# 使用
async with BleConnection(address) as client:
    await client.write_gatt_char(char_uuid, data)
```

### 6.3 事件驱动架构

**事件系统**：
```python
from typing import Callable, Awaitable

class EventEmitter:
    def __init__(self):
        self._listeners: list[Callable[..., Awaitable[None]]] = []
    
    def on(self, callback: Callable[..., Awaitable[None]]):
        """注册监听器"""
        self._listeners.append(callback)
    
    async def emit(self, *args, **kwargs):
        """触发事件"""
        for listener in self._listeners:
            await listener(*args, **kwargs)

# 使用
events = EventEmitter()

@events.on
async def on_button_press(data: bytes):
    """按钮事件处理"""
    _LOGGER.info(f"按钮按下: {data.hex()}")

await events.emit(b'\x01')
```

---

## 7. bleak库使用指南

### 7.1 扫描设备

```python
from bleak import BleakScanner

async def scan_devices(timeout: float = 5.0):
    """扫描BLE设备"""
    devices = []
    
    def detection_callback(device, advertisement_data):
        devices.append((device.name, device.address))
        _LOGGER.info(f"发现设备: {device.name} ({device.address})")
    
    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()
    
    return devices
```

### 7.2 连接与断开

```python
from bleak import BleakClient

async def connect_device(address: str, timeout: float = 10.0):
    """连接设备"""
    client = BleakClient(address, timeout=timeout)
    
    try:
        await client.connect()
        _LOGGER.info(f"连接成功: {address}")
        return client
    except Exception as e:
        _LOGGER.error(f"连接失败: {e}")
        raise
```

### 7.3 读写操作

```python
async def read_characteristic(client, char_uuid: str):
    """读取特征"""
    data = await client.read_gatt_char(char_uuid)
    _LOGGER.info(f"读取数据: {data.hex()}")
    return data

async def write_characteristic(client, char_uuid: str, data: bytes):
    """写入特征"""
    await client.write_gatt_char(char_uuid, data)
    _LOGGER.info(f"写入数据: {data.hex()}")

async def subscribe_notify(client, char_uuid: str, callback):
    """订阅通知"""
    await client.start_notify(char_uuid, callback)
    _LOGGER.info("已订阅通知")
```

---

## 8. 错误处理与重连策略

### 8.1 错误处理

**异常类型**：
```python
from bleak.exc import BleakError, BleakDeviceNotFoundError

async def safe_connect(address: str, max_retries: int = 3):
    """安全连接（带重试）"""
    for attempt in range(max_retries):
        try:
            client = BleakClient(address)
            await client.connect()
            return client
        
        except BleakDeviceNotFoundError:
            _LOGGER.error(f"设备未找到: {address}")
            raise
        
        except BleakError as e:
            _LOGGER.warning(f"连接失败(尝试{attempt+1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # 指数退避
            else:
                raise
```

### 8.2 自动重连

**重连策略**：
```python
class AutoReconnectClient:
    def __init__(self, address: str, max_retries: int = 5):
        self.address = address
        self.max_retries = max_retries
        self.client = None
        self._reconnect_task = None
    
    async def connect(self):
        """连接设备"""
        for attempt in range(self.max_retries):
            try:
                self.client = BleakClient(self.address)
                await self.client.connect()
                
                # 启动断开监听
                self._start_disconnect_monitor()
                
                return self.client
            
            except Exception as e:
                _LOGGER.warning(f"连接失败(尝试{attempt+1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
    
    def _start_disconnect_monitor(self):
        """启动断开监听"""
        async def monitor():
            while self.client and self.client.is_connected:
                await asyncio.sleep(1)
            
            _LOGGER.warning("连接断开，尝试重连...")
            await self.connect()
        
        self._reconnect_task = asyncio.create_task(monitor())
```

### 8.3 超时处理

**设置超时**：
```python
import asyncio

async def connect_with_timeout(address: str, timeout: float = 10.0):
    """带超时的连接"""
    try:
        client = BleakClient(address)
        
        # 使用asyncio.wait_for设置超时
        await asyncio.wait_for(client.connect(), timeout=timeout)
        
        return client
    
    except asyncio.TimeoutError:
        _LOGGER.error(f"连接超时: {address}")
        raise
```

---

## 9. 性能优化技巧

### 9.1 减少GATT操作

**缓存服务和特征**：
```python
class CachedBleClient:
    def __init__(self, address: str):
        self.address = address
        self.client = None
        self._service_cache = {}
        self._char_cache = {}
    
    async def get_characteristic(self, char_uuid: str):
        """获取特征（带缓存）"""
        if char_uuid in self._char_cache:
            return self._char_cache[char_uuid]
        
        # 服务发现
        services = await self.client.get_services()
        
        for service in services:
            for char in service.characteristics:
                if char.uuid == char_uuid:
                    self._char_cache[char_uuid] = char
                    return char
        
        raise ValueError(f"特征未找到: {char_uuid}")
```

### 9.2 批量操作

**使用asyncio.gather**：
```python
async def batch_read(client, char_uuids: list[str]):
    """批量读取"""
    tasks = [
        client.read_gatt_char(uuid) 
        for uuid in char_uuids
    ]
    results = await asyncio.gather(*tasks)
    return results
```

### 9.3 连接复用

**保持长连接**：
```python
class PersistentConnection:
    def __init__(self, address: str, keep_alive_interval: float = 30.0):
        self.address = address
        self.keep_alive_interval = keep_alive_interval
        self.client = None
        self._keep_alive_task = None
    
    async def connect(self):
        """连接并保持"""
        self.client = BleakClient(self.address)
        await self.client.connect()
        
        # 启动保活任务
        self._keep_alive_task = asyncio.create_task(
            self._keep_alive()
        )
    
    async def _keep_alive(self):
        """保活"""
        while self.client.is_connected:
            await asyncio.sleep(self.keep_alive_interval)
            # 可以发送心跳包
```

---

## 10. 完整代码示例

### 10.1 设备管理器

```python
import asyncio
import logging
from typing import Callable, Awaitable
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

_LOGGER = logging.getLogger(__name__)

SERVICE_UUID = "0000FFE0-0000-1000-8000-00805F9B34FB"
CHAR_NOTIFY_UUID = "0000FFE1-0000-1000-8000-00805F9B34FB"
CHAR_WRITE_UUID = "0000FFE2-0000-1000-8000-00805F9B34FB"

class AntiLossTagDevice:
    """防丢标签设备"""
    
    def __init__(self, address: str, name: str = None):
        self.address = address
        self.name = name or address
        self.client: BleakClient | None = None
        self._connected = False
        self._notify_callback: Callable[[bytes], Awaitable[None]] | None = None
    
    async def connect(self, timeout: float = 10.0) -> bool:
        """连接设备"""
        try:
            self.client = BleakClient(self.address, timeout=timeout)
            await self.client.connect()
            
            # 验证服务
            services = await self.client.get_services()
            if not any(s.uuid == SERVICE_UUID for s in services):
                raise ValueError("FFE0服务未发现")
            
            self._connected = True
            _LOGGER.info(f"连接成功: {self.name}")
            return True
        
        except Exception as e:
            _LOGGER.error(f"连接失败: {e}")
            self._connected = False
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.client and self._connected:
            await self.client.disconnect()
            self._connected = False
            _LOGGER.info(f"已断开: {self.name}")
    
    async def subscribe_notify(
        self, 
        callback: Callable[[bytes], Awaitable[None]]
    ):
        """订阅通知"""
        if not self._connected or not self.client:
            raise ValueError("未连接")
        
        await self.client.start_notify(CHAR_NOTIFY_UUID, callback)
        self._notify_callback = callback
        _LOGGER.info(f"已订阅通知: {self.name}")
    
    async def write_control(self, data: bytes):
        """写入控制数据"""
        if not self._connected or not self.client:
            raise ValueError("未连接")
        
        await self.client.write_gatt_char(CHAR_WRITE_UUID, data)
        _LOGGER.debug(f"写入数据: {data.hex()}")
    
    async def set_alarm(
        self, 
        enable: bool, 
        distance: int, 
        alarm_type: int = 0x00
    ):
        """设置报警"""
        command = bytes([
            0xA0,
            0x01 if enable else 0x00,
            distance,
            alarm_type,
            0x00, 0x00, 0x00, 0x00
        ])
        await self.write_control(command)
    
    async def set_mute(self, duration: int):
        """设置静音"""
        command = bytes([
            0xA1,
            duration,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ])
        await self.write_control(command)
    
    @property
    def connected(self) -> bool:
        """连接状态"""
        return self._connected and self.client is not None
```

### 10.2 使用示例

```python
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    """主函数"""
    # 扫描设备
    print("扫描设备...")
    devices = await BleakScanner.discover(timeout=5.0)
    
    for device in devices:
        if device.name and "KT6368A" in device.name:
            print(f"发现设备: {device.name} ({device.address})")
            
            # 连接设备
            tag = AntiLossTagDevice(device.address, device.name)
            
            if await tag.connect():
                # 订阅通知
                async def on_notify(sender, data):
                    print(f"收到通知: {data.hex()}")
                
                await tag.subscribe_notify(on_notify)
                
                # 设置报警
                await tag.set_alarm(
                    enable=True,
                    distance=5,
                    alarm_type=0x00
                )
                
                # 保持连接
                try:
                    await asyncio.sleep(60)
                finally:
                    await tag.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 参考文档

- [Bluetooth Core Specification 5.1](https://www.bluetooth.com/specifications/bluetooth-core-specification/)
- [KT6368A芯片数据手册](../参考资料/KT6368A固件文档.md)
- [bleak库官方文档](https://bleak.readthedocs.io/)
- [Python异步编程指南](https://docs.python.org/3/library/asyncio.html)
- [Home Assistant集成文档](https://developers.home-assistant.io/docs/integration_fetching/)

---

**文档版本**: v1.0  
**最后更新**: 2025-02-08  
**维护者**: anti_loss_tag 项目组
