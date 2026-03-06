# BLE安全指南

> **低功耗蓝牙安全最佳实践**
> 
**目标读者**：开发者、安全工程师  
**难度等级**：⭐⭐⭐⭐ 高级  
**最后更新**：2025-03-06

---

## 一、BLE安全风险概述

### 1.1 主要安全威胁

```
┌─────────────────────────────────────────┐
│          BLE安全威胁模型                 │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────┐      ┌──────────┐        │
│  │  攻击者   │─────▶│  BLE设备 │        │
│  └──────────┘      └────┬─────┘        │
│                           │             │
│         ┌─────────────────┼──────────┐ │
│         ▼                 ▼          ▼ │
│   ┌──────────┐     ┌──────────┐  ┌────┴─┐
│   │ MITM攻击 │     │ 窃听攻击  │  │跟踪攻击│
│   └──────────┘     └──────────┘  └──────┘
│                                         │
└─────────────────────────────────────────┘
```

### 1.2 风险分类

| 威胁类型 | 风险等级 | 影响范围 | 防护难度 |
|---------|---------|---------|---------|
| **MITM攻击** | 🔴 高 | 通信安全 | 中等 |
| **窃听攻击** | 🔴 高 | 数据隐私 | 中等 |
| **设备跟踪** | 🟡 中 | 用户隐私 | 困难 |
| **重放攻击** | 🟡 中 | 数据完整性 | 简单 |
| **固件漏洞** | 🟡 中 | 设备安全 | 困难 |
| **拒绝服务** | 🟢 低 | 可用性 | 简单 |

---

## 二、MITM攻击防护

### 2.1 攻击原理

**MITM（Man-in-the-Middle）中间人攻击**：

```
正常通信：
设备A ◄───────► 设备B

MITM攻击：
设备A ◄──► 攻击者 ◄──► 设备B
         (拦截/修改/转发)
```

### 2.2 BLE配对安全等级

BLE定义了4种配对模式（安全性从低到高）：

| 模式 | 安全性 | 说明 | 防护能力 |
|------|--------|------|---------|
| **Just Works** | ⚠️ 低 | 无认证，仅加密 | ❌ 无MITM防护 |
| **Passkey Entry** | ✅ 高 | 6位PIN码 | ✅ MITM防护 |
| **Numeric Comparison** | ✅ 高 | 6位数字比对 | ✅ MITM防护 |
| **OOB (Out-of-Band)** | ✅ 最高 | NFC/可见光等 | ✅ MITM防护 |

### 2.3 "Just Works"安全风险

**问题描述**：
- 大多数BLE设备使用"Just Works"配对
- **无MITM防护**
- 依赖用户手动验证（但很多用户不验证）

**攻击场景**：
```python
# 攻击者可以：
1. 拦截配对请求
2. 伪装成合法设备
3. 接受配对请求
4. 窃听/修改通信数据
```

**防护建议**：

#### 方案1：使用Passkey Entry（推荐）

```python
# 设备端实现示例（伪代码）
def pairing_with_passkey():
    # 1. 生成6位随机PIN
    pin = generate_random_pin()  # 例如：123456
    
    # 2. 显示PIN在设备屏幕或LED
    display_pin(pin)
    
    # 3. 要求用户在HA输入相同PIN
    user_input = await get_passkey_from_user()
    
    # 4. 验证PIN
    if user_input == pin:
        # 配对成功，启用MITM防护
        enable_encryption(mitm_protection=True)
    else:
        # 配对失败
        reject_pairing()
```

#### 方案2：应用层加密（备选）

```python
# 即使BLE配对使用Just Works，
# 也可以在应用层添加加密

import hashlib
import hmac

def encrypt_application_data(data, shared_secret):
    """应用层加密"""
    # 使用HMAC-SHA256
    signature = hmac.new(
        shared_secret, 
        data, 
        hashlib.sha256
    ).digest()
    
    return data + signature

def verify_application_data(data_with_signature, shared_secret):
    """验证数据完整性"""
    data = data_with_signature[:-32]
    signature = data_with_signature[-32:]
    
    expected = hmac.new(
        shared_secret, 
        data, 
        hashlib.sha256
    ).digest()
    
    return hmac.compare_digest(signature, expected)
```

### 2.4 KT6368A安全配置

KT6368A芯片支持的安全功能：

```c
// AT指令配置安全参数

// 1. 设置配对模式（Passkey Entry）
AT+PAIRMODE=2

// 2. 设置加密使能
AT+ENCRYPT=1

// 3. 设置PIN码（6位数字）
AT+PIN=123456

// 4. 设置IO能力（KeyboardOnly）
AT+IOCAP=2

// 5. 保存配置
AT+SAVE
```

**注意**：KT6368A的"Passkey Entry"需要硬件支持（按键输入），防丢标签可能需要简化方案。

---

## 三、数据加密和完整性

### 3.1 BLE加密层级

BLE提供多层级加密：

```
┌─────────────────────────────────────┐
│         BLE加密层级                 │
├─────────────────────────────────────┤
│ Layer 3: 应用层加密（推荐）        │
│          - AES-128                  │
│          - 端到端加密               │
├─────────────────────────────────────┤
│ Layer 2: BLE链路层加密（自动）     │
│          - AES-CCM                  │
│          - 配对后自动启用           │
├─────────────────────────────────────┤
│ Layer 1: 物理层（无加密）          │
│          - 2.4GHz射频              │
└─────────────────────────────────────┘
```

### 3.2 推荐加密方案

#### 方案A：仅使用BLE链路层加密（简单）

**优点**：
- ✅ 无需额外代码
- ✅ 硬件加速，性能好
- ✅ 符合BLE标准

**缺点**：
- ⚠️ 依赖配对安全性
- ⚠️ 密钥管理依赖BLE栈

**适用场景**：
- 对安全性要求中等
- 设备资源受限
- 快速开发

#### 方案B：应用层+BLE链路层（推荐）

**优点**：
- ✅ 端到端加密
- ✅ 不依赖BLE配对安全性
- ✅ 密钥自主管理

**实现示例**：

```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os

class ApplicationLayerEncryption:
    """应用层加密"""
    
    def __init__(self, shared_secret: bytes):
        """初始化加密器
        
        Args:
            shared_secret: 预共享密钥（16/24/32字节）
        """
        if len(shared_secret) not in [16, 24, 32]:
            raise ValueError("密钥长度必须是16/24/32字节")
        
        self.key = shared_secret
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """加密数据"""
        # 生成随机IV
        iv = os.urandom(16)
        
        # 创建加密器
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # 填充（PKCS7）
        padding_length = 16 - (len(plaintext) % 16)
        plaintext += bytes([padding_length] * padding_length)
        
        # 加密
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        # 返回 IV + 密文
        return iv + ciphertext
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        """解密数据"""
        # 提取IV
        iv = ciphertext[:16]
        actual_ciphertext = ciphertext[16:]
        
        # 创建解密器
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # 解密
        plaintext = decryptor.update(actual_ciphertext) + decryptor.finalize()
        
        # 移除填充
        padding_length = plaintext[-1]
        return plaintext[:-padding_length]
```

### 3.3 密钥管理

#### 密钥生成

```python
import secrets

def generate_shared_key(length: int = 32) -> bytes:
    """生成安全的共享密钥
    
    Args:
        length: 密钥长度（16/24/32字节）
    
    Returns:
        随机密钥
    """
    return secrets.token_bytes(length)
```

#### 密钥存储

**⚠️ 禁止**：
- ❌ 硬编码密钥在代码中
- ❌ 明文存储密钥
- ❌ 将密钥提交到Git

**✅ 推荐**：
- ✅ 使用Home Assistant的secrets.yaml
- ✅ 使用环境变量
- ✅ 使用密钥管理服务（如Vault）

**配置示例**：

```yaml
# configuration.yaml
anti_loss_tag:
  encryption_key: !secret ble_encryption_key
```

---

## 四、隐私保护

### 4.1 设备跟踪风险

**问题描述**：
- BLE设备广播唯一的MAC地址
- 攻击者可以部署监听器跟踪设备
- 泄露用户位置和行动轨迹

**攻击场景**：
```
商场/机场/公共场所
    ↓
部署BLE监听器
    ↓
记录设备MAC地址
    ↓
分析用户行为模式
```

### 4.2 MAC地址随机化

BLE 4.2+支持MAC地址随机化：

**两种类型**：
1. **静态地址** - 固定，可跟踪
2. **随机地址** - 定期变化，防跟踪

**隐私类型**：
- **Network Privacy** - 使用随机地址扫描
- **Device Privacy** - 使用随机地址广播

#### KT6368A配置

```c
// 启用MAC地址随机化
AT+RANDADDR=1

// 设置地址变化周期（秒）
AT+RANDINT=900  // 每15分钟变化一次

// 保存配置
AT+SAVE
```

### 4.3 广播数据最小化

**原则**：减少广播中的敏感信息

❌ **不安全示例**：
```
广播数据：
- 设备名称：My Tracker
- 用户名：John
- 位置：Home
```

✅ **安全示例**：
```
广播数据：
- 设备类型：0x01（通用）
- UUID：自定义（不含敏感信息）
- 制造商ID：0xFFFF
```

### 4.4 GDPR合规建议

**实施建议**：

1. **数据最小化**
```python
# 只收集必要数据
device_data = {
    "battery": battery_level,
    "rssi": signal_strength,
    "device_id": hashed_id,  # 匿名化
}
```

2. **数据匿名化**
```python
import hashlib

def anonymize_device_id(mac_address: str) -> str:
    """匿名化设备ID"""
    return hashlib.sha256(mac_address.encode()).hexdigest()
```

---

## 五、固件安全

### 5.1 固件更新安全

**风险**：
- 恶意固件更新
- 固件回滚攻击
- 更新过程被劫持

**防护措施**：

#### 1. 固件签名验证

```python
import hmac
import hashlib

def verify_firmware_signature(firmware_data: bytes, signature: bytes, secret_key: bytes) -> bool:
    """验证固件签名"""
    expected_signature = hmac.new(
        secret_key,
        firmware_data,
        hashlib.sha256
    ).digest()
    
    return hmac.compare_digest(signature, expected_signature)
```

#### 2. 版本反回滚

```python
def check_firmware_version(new_version: str, current_version: str) -> bool:
    """检查固件版本（防止回滚）"""
    new = tuple(map(int, new_version.split(".")))
    current = tuple(map(int, current_version.split(".")))
    
    return new >= current
```

---

## 六、安全测试

### 6.1 渗透测试工具

- **Ubertooth** - BLE嗅探器
- **GATTacker** - GATT攻击工具
- **InternalBlue** - 蓝牙栈分析框架

### 6.2 安全检查清单

```markdown
## 密钥管理
- [ ] 无硬编码密钥
- [ ] 密钥存储安全
- [ ] 密钥定期轮换

## 加密实现
- [ ] 使用标准加密库
- [ ] 避免自己实现加密算法
- [ ] 使用安全随机数生成器

## 输入验证
- [ ] 验证所有外部输入
- [ ] 防止缓冲区溢出
- [ ] 限制数据大小
```

---

## 七、安全最佳实践总结

### 7.1 开发阶段

1. **设计阶段**
   - ✅ 安全设计原则（Security by Design）
   - ✅ 最小权限原则
   - ✅ 深度防御

2. **实现阶段**
   - ✅ 使用标准加密库
   - ✅ 启用BLE加密和认证
   - ✅ 实施应用层加密

3. **测试阶段**
   - ✅ 进行安全测试
   - ✅ 代码审查
   - ✅ 第三方安全评估

### 7.2 部署阶段

1. **配置安全**
   - ✅ 禁用不必要的功能
   - ✅ 启用MAC地址随机化
   - ✅ 使用强密钥

2. **监控和响应**
   - ✅ 记录安全事件
   - ✅ 异常行为检测
   - ✅ 定期安全审计

---

## 八、常见问题（FAQ）

### Q1: Just Works配对完全不安全吗？

**A**: 不完全是。Just Works仍然提供加密（防止窃听），但**无法防止MITM攻击**。对于低价值设备（如防丢标签），可以接受，但建议添加应用层加密。

### Q2: 如何选择加密方案？

**A**:
- **简单场景**：仅使用BLE链路层加密
- **高安全性**：BLE链路层 + 应用层加密
- **最高安全性**：端到端加密 + 硬件安全模块

### Q3: MAC地址随机化会影响连接吗？

**A**: 可能影响。需要确保：
- 设备和中央设备都支持隐私功能
- 使用设备身份地址（Identity Address）作为连接地址
- Home Assistant蓝牙栈支持BLE 4.2+

---

## 九、参考资料

1. **Bluetooth SIG安全规范**
   - [Bluetooth Core Specification v5.3 - Security]
   - [Security Best Practices]

2. **学术研究**
   - [BLE Security Analysis]
   - [MITM Attacks on BLE]

3. **工具和框架**
   - [Ubertooth - BLE Sniffer]
   - [GATTacker - GATT Exploitation Tool]

4. **Home Assistant**
   - [Bluetooth Integration Blueprint]
   - [Security and Privacy Guidelines]

---

**最后更新**：2025-03-06  
**版本**：1.0.0
