# Python BLE集成开发指南

**文档版本**: v2.0  
**制定日期**: 2025-02-08  
**技术栈**: Python 3.11+ / bleak / Home Assistant  
**适用范围**: BLE设备集成开发

---

## 1. 开发环境搭建

### 1.1 系统要求

- **操作系统**: Linux（推荐）、macOS、Windows 10+
- **Python版本**: 3.11或更高
- **BLE硬件**: 支持BLE 5.0的蓝牙适配器
- **Home Assistant**: 2024.1.0或更高

### 1.2 依赖安装

```bash
# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install bleak>=0.21.0
pip install bleak-retry-connector>=3.0.0
pip install homeassistant
```

### 1.3 开发工具

- **IDE**: VS Code + Python扩展
- **调试工具**: 
  - `btmon`（Linux）
  - BLE Sniffer（跨平台）
- **代码检查**: ruff、mypy

---

## 2. BLE基础概念

### 2.1 GATT协议层次

```
GATT Server (KT6368A设备)
├── Service (FFE0: Anti-loss Tag Service)
│   ├── Characteristic (FFE1: Notify)
│   │   ├── Value (0x01, 0x02, ...)
│   │   └── CCC (Client Characteristic Configuration)
│   └── Characteristic (FFE2: Write)
│       └── Value (可写入数据)
```

### 2.2 UUID定义

KT6368A芯片使用128位UUID：

```python
# FFE0服务（主服务）
UUID_SERVICE_FFE0 = "0000ffe0-0000-1000-8000-00805f9b34fb"

# FFE1特征（通知）
UUID_NOTIFY_FFE1 = "0000ffe1-0000-1000-8000-00805f9b34fb"

# FFE2特征（写入）
UUID_WRITE_FFE2 = "0000ffe2-0000-1000-8000-00805f9b34fb"
```

---

## 3. Python异步编程

### 3.1 基础模式

#### 3.1.1 协程（Coroutine）

```python
import asyncio

async def connect_device(address: str) -> bool:
    """异步连接设备"""
    # 模拟连接操作
    await asyncio.sleep(1)  # 模拟异步等待
    return True

# 调用协程
async def main():
    result = await connect_device("AA:BB:CC:DD:EE:FF")
    print(f"连接结果: {result}")

asyncio.run(main())
```

#### 3.1.2 任务管理

```python
async def monitor_device(device):
    """监控设备"""
    while True:
        await device.check_status()
        await asyncio.sleep(5)

async def main():
    # 创建任务
    device = AntiLossTagDevice("AA:BB:CC:DD:EE:FF")
    task = asyncio.create_task(monitor_device(device))
    
    # 等待一段时间
    await asyncio.sleep(60)
    
    # 取消任务
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("任务已取消")
```

### 3.2 并发控制

#### 3.2.1 信号量（Semaphore）

```python
class BleConnectionManager:
    """BLE连接管理器"""
    
    _slots = asyncio.Semaphore(3)  # 限制3个并发连接
    
    @classmethod
    async def connect(cls, address: str):
        """连接设备（带并发控制）"""
        await cls._slots.acquire()
        try:
            # 执行连接
            client = BleakClient(address)
            await client.connect()
            return client
        finally:
            cls._slots.release()
```

#### 3.2.2 锁（Lock）

```python
class Device:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._data = {}
    
    async def update_data(self, key: str, value: any):
        """更新数据（线程安全）"""
        async with self._lock:
            self._data[key] = value
```

---

## 4. bleak库使用

### 4.1 设备扫描

```python
from bleak import BleakScanner
from bleak.backends.device import BLEDevice

async def scan_devices(timeout: float = 5.0) -> list[BLEDevice]:
    """扫描BLE设备"""
    devices = []
    
    def detection_callback(device: BLEDevice, advertisement_data):
        devices.append(device)
        print(f"发现设备: {device.name} ({device.address})")
    
    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()
    
    return devices

# 使用
asyncio.run(scan_devices())
```

### 4.2 连接设备

```python
from bleak import BleakClient

async def connect_to_device(address: str):
    """连接到设备"""
    async with BleakClient(address) as client:
        print(f"已连接: {client.is_connected}")
        
        # 发现服务
        services = await client.get_services()
        for service in services:
            print(f"服务: {service.uuid}")
            for char in service.characteristics:
                print(f"  特征: {char.uuid}")
```

### 4.3 读写特征

```python
async def read_characteristic(client: BleakClient, char_uuid: str):
    """读取特征值"""
    value = await client.read_gatt_char(char_uuid)
    print(f"读取值: {value.hex()}")
    return value

async def write_characteristic(client: BleakClient, char_uuid: str, data: bytes):
    """写入特征值"""
    await client.write_gatt_char(char_uuid, data)
    print(f"写入值: {data.hex()}")

async def start_notify(client: BleakClient, char_uuid: str, callback):
    """开启通知"""
    await client.start_notify(char_uuid, callback)
    print(f"已开启通知: {char_uuid}")
```

---

## 5. 数据协议实现

### 5.1 数据包构建

```python
class PacketBuilder:
    """数据包构建器"""
    
    @staticmethod
    def build_command(cmd: int, payload: bytes = b"") -> bytes:
        """构建命令包"""
        packet = bytes([cmd]) + payload
        
        # 计算校验和（简单累加）
        checksum = sum(packet) & 0xFF
        packet += bytes([checksum])
        
        return packet
    
    @staticmethod
    def parse_packet(data: bytes) -> dict:
        """解析数据包"""
        if len(data) < 2:
            raise ValueError("数据包太短")
        
        cmd = data[0]
        payload = data[1:-1]
        checksum = data[-1]
        
        # 验证校验和
        calculated = (sum(data[:-1]) & 0xFF)
        if checksum != calculated:
            raise ValueError(f"校验和错误: 期望{calculated}, 实际{checksum}")
        
        return {
            "command": cmd,
            "payload": payload,
            "checksum": checksum,
            "valid": True
        }

# 使用示例
builder = PacketBuilder()
packet = builder.build_command(0x01, bytes([0x03]))
print(f"命令包: {packet.hex()}")  # 输出: 010304

parsed = builder.parse_packet(packet)
print(f"解析结果: {parsed}")
```

### 5.2 命令定义

```python
class CommandCode:
    """命令代码定义"""
    # 设置命令
    SET_DISTANCE = 0x01        # 设置报警距离
    SET_MUTE = 0x02            # 设置静音
    SET_SWITCH = 0x03          # 设置开关
    
    # 查询命令
    QUERY_STATUS = 0x10        # 查询状态
    QUERY_BATTERY = 0x11       # 查询电量
    QUERY_VERSION = 0x12       # 查询版本
    
    # 响应代码
    RESPONSE_OK = 0x00         # 成功
    RESPONSE_ERROR = 0xFF      # 失败

class DistanceLevel:
    """距离等级"""
    NEAR = 0x01  # 近距离（< 2米）
    MEDIUM = 0x02  # 中距离（2-5米）
    FAR = 0x03  # 远距离（5-10米）
```

### 5.3 完整通信示例

```python
async def full_communication_example():
    """完整通信示例"""
    address = "AA:BB:CC:DD:EE:FF"
    
    async with BleakClient(address) as client:
        # 1. 设置距离
        cmd = PacketBuilder.build_command(
            CommandCode.SET_DISTANCE,
            bytes([DistanceLevel.MEDIUM])
        )
        await client.write_gatt_char(UUID_WRITE_FFE2, cmd)
        
        # 2. 读取状态
        response = await client.read_gatt_char(UUID_NOTIFY_FFE1)
        parsed = PacketBuilder.parse_packet(response)
        print(f"状态: {parsed}")
        
        # 3. 开启通知
        def notification_handler(sender, data):
            parsed = PacketBuilder.parse_packet(data)
            print(f"收到通知: {parsed}")
        
        await client.start_notify(UUID_NOTIFY_FFE1, notification_handler)
        
        # 保持连接
        await asyncio.sleep(10)
```

---

## 6. Home Assistant集成

### 6.1 Config Flow

```python
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

class AntiLossTagConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """配置流程"""
    
    VERSION = 1
    
    async def async_step_bluetooth(
        self,
        discovery_info: dict
    ) -> FlowResult:
        """蓝牙发现步骤"""
        self.context["title"] = "KT6368A防丢标签"
        
        # 设置唯一ID
        await self.async_set_unique_id(discovery_info["address"])
        self._abort_if_unique_id_configured()
        
        # 进入下一步
        return await self.async_step_confirm()
    
    async def async_step_confirm(
        self,
        user_input: dict | None = None
    ) -> FlowResult:
        """确认步骤"""
        if user_input is not None:
            # 保存配置
            return self.async_create_entry(
                title="KT6368A防丢标签",
                data={
                    "address": self._address,
                    "name": user_input.get("name", "防丢标签")
                }
            )
        
        # 显示表单
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({
                vol.Optional("name", default="防丢标签"): str
            })
        )
```

### 6.2 传感器实体

```python
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant

class AntiLossTagBatterySensor(SensorEntity):
    """电池电量传感器"""
    
    def __init__(self, device):
        self._device = device
        self._attr_name = "电池电量"
        self._attr_native_unit_of_measurement = "%"
        self._attr_device_class = SensorDeviceClass.BATTERY
    
    @property
    def unique_id(self) -> str:
        """唯一ID"""
        return f"{self._device.address}_battery"
    
    @property
    def native_value(self) -> int | None:
        """电量值"""
        return self._device.battery
```

---

## 7. 错误处理

### 7.1 异常分类

```python
class BLEError(Exception):
    """BLE错误基类"""
    pass

class DeviceNotFoundError(BLEError):
    """设备未找到"""
    pass

class ConnectionError(BLEError):
    """连接失败"""
    pass

class ServiceNotFoundError(BLEError):
    """服务未找到"""
    pass

class ChecksumError(BLEError):
    """校验和错误"""
    pass
```

### 7.2 错误处理模式

```python
async def safe_connect(address: str, max_retries: int = 3) -> BleakClient:
    """安全连接（带重试）"""
    for attempt in range(max_retries):
        try:
            client = BleakClient(address)
            await client.connect()
            return client
        
        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                await asyncio.sleep(wait_time)
            else:
                raise ConnectionError(f"连接失败，已重试{max_retries}次")
        
        except Exception as e:
            raise BLEError(f"未知错误: {e}")
```

---

## 8. 调试技巧

### 8.1 日志配置

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# bleak库日志
logging.getLogger('bleak').setLevel(logging.DEBUG)

# 本项目日志
_LOGGER = logging.getLogger(__name__)
```

### 8.2 BLE抓包

```bash
# Linux
sudo btmon

# 或使用hcitool
sudo hcitool lescan

# Windows
# 使用BLE Sniffer应用

# macOS
# 使用Xcode的Bluetooth工具
```

---

## 9. 性能优化

### 9.1 连接池

```python
class ConnectionPool:
    """连接池"""
    
    def __init__(self, max_connections: int = 3):
        self._semaphore = asyncio.Semaphore(max_connections)
        self._connections: dict[str, BleakClient] = {}
    
    async def get_connection(self, address: str) -> BleakClient:
        """获取连接"""
        await self._semaphore.acquire()
        
        if address not in self._connections:
            client = BleakClient(address)
            await client.connect()
            self._connections[address] = client
        
        return self._connections[address]
    
    async def release_connection(self, address: str):
        """释放连接"""
        self._semaphore.release()
```

### 9.2 批量操作

```python
async def batch_write_characteristics(
    client: BleakClient,
    operations: list[tuple[str, bytes]]
):
    """批量写入特征"""
    for uuid, data in operations:
        await client.write_gatt_char(uuid, data)
        await asyncio.sleep(0.01)  # 短暂延迟，避免过载
```

---

## 10. 测试

### 10.1 单元测试

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_device_connection():
    """测试设备连接"""
    # Mock bleak客户端
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock(return_value=None)
    mock_client.is_connected = True
    
    # 测试连接
    device = AntiLossTagDevice("AA:BB:CC:DD:EE:FF")
    device._client = mock_client
    
    await device.connect()
    assert device.connected
```

### 10.2 集成测试

```python
@pytest.mark.asyncio
async def test_full_communication():
    """测试完整通信"""
    # 需要真实设备或模拟器
    address = os.getenv("TEST_DEVICE_ADDRESS")
    
    async with BleakClient(address) as client:
        # 写入
        cmd = PacketBuilder.build_command(0x01, bytes([0x03]))
        await client.write_gatt_char(UUID_WRITE_FFE2, cmd)
        
        # 读取
        response = await client.read_gatt_char(UUID_NOTIFY_FFE1)
        assert len(response) > 0
```

---

## 11. 部署

### 11.1 Home Assistant安装

```bash
# 复制到Home Assistant
cp -r custom_components/anti_loss_tag \
    ~/.homeassistant/custom_components/

# 重启Home Assistant
hassio homeassistant restart
```

### 11.2 配置

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.anti_loss_tag: debug
```

---

## 12. 参考资源

- [bleak官方文档](https://bleak.readthedocs.io/)
- [Home Assistant集成开发](https://developers.home-assistant.io/)
- [Python异步编程](https://docs.python.org/3/library/asyncio.html)
- [Bluetooth Core Specification](https://www.bluetooth.com/specifications/)

---

**文档状态**: 已完成  
**最后更新**: 2025-02-08  
**适用版本**: v1.6.0+
