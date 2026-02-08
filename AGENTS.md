# AGENTS.md - Home Assistant KT6368A 防丢标签集成开发指南

本文档为 AI 编码助手（agentic coding agents）提供项目规范和最佳实践。

## 项目概述

- **类型**: Home Assistant 自定义集成（KT6368A BLE 防丢标签）
- **芯片**: **KT6368A 双模蓝牙5.1 SoC（SOP-8封装）** - **专门适配**
- **官方参考**: LenzeTech iSearching Two Android应用（739行Java代码）
  - 应用名称：iSearching Two
  - 开发商：LenzeTech（深圳岚至科技）
  - 代码位置：archive/temp_files/
  - 验证：FFE0/FFE1/FFE2协议完整实现
- **语言**: Python 3.11+
- **主要依赖**: bleak >= 0.21.0, bleak-retry-connector >= 3.0.0
- **代码位置**: `custom_components/anti_loss_tag/`

**官方参考验证**：
本集成基于LenzeTech官方Android应用（iSearching Two）的BLE协议实现，
所有FFE0/FFE1/FFE2协议操作均已通过官方代码验证。

参考文档：
- [Java代码审核](docs/Java参考/Java代码审核.md) - 官方代码架构分析
- [Java到Python移植指南](docs/Java参考/Java到Python移植指南.md) - Python实现参考

---

## 0. 法律与安全审查要求（必须遵守）

**所有代码变更必须经过以下审查**：

### 0.1 敏感信息检查（每次提交前必须执行）

**禁止提交的内容**：
- 密码、密钥、证书（.key, .pem, .cert, .p12, .pfx）
- 环境变量文件（.env, .env.local）
- 个人隐私信息（IP地址、邮箱、电话）
- 硬编码的凭据（API密钥、Token）
- 内部服务器地址（除非是示例且明确标注）

**审查方法**：
```bash
# 检查Git历史中的敏感文件
git log --all --full-history --pretty=format:"%H" | while read hash; do git ls-tree -r $hash | awk '{print $2}'; done | sort -u | grep -E "\.(key|pem|cert|crt|p12|pfx|secret|id_rsa|id_dsa|jwt|env)$"

# 搜索代码中的敏感关键词
grep -r "password\|secret\|api_key\|token\|private_key" --include="*.py" --include="*.json" -n
```

### 0.2 法律风险审查

**第三方代码使用**：
- 必须明确标注第三方代码来源
- 必须检查许可证兼容性
- 必须在文档中说明依赖关系

**知识产权**：
- 不得复制他人受版权保护的代码
- 参考代码必须重写，不能直接复制
- 必须保留原始许可证声明（如适用）

**免责声明**：
- README必须包含使用风险警告
- 必须明确说明"按原样提供，无保证"
- 必须声明不承担任何责任

### 0.3 用户隐私保护

**数据收集限制**：
- 不得收集用户个人信息
- BLE设备地址应匿名化处理
- 日志中不得包含敏感信息

**数据存储**：
- 不得存储用户隐私数据
- 连接信息应仅用于功能实现
- 必须遵守GDPR/CCPA等隐私法规

### 0.4 安全最佳实践

**通信安全**：
- BLE通信使用加密（如设备支持）
- 不得明文传输敏感数据
- 实施适当的认证机制

**输入验证**：
- 所有外部输入必须验证
- 防止注入攻击
- 限制权限范围

---

## 1. 构建、Lint 和测试命令

### 本地开发

开发时将代码复制到 Home Assistant 自定义组件目录。重启 Home Assistant 或通过界面重新加载核心配置。

### 代码质量检查（建议添加）

使用 ruff 进行代码检查和格式化（检查目标：custom_components/anti_loss_tag/）。使用 mypy 进行类型检查。使用 hass 脚本验证 Home Assistant 配置（参数：--script check_config --path 配置目录路径）。

### 运行单个测试（未来）

当前使用 pytest 作为测试框架。测试文件位于 tests/ 目录。运行测试时使用 pytest 命令，可指定测试文件和测试函数。

---

## 2. 代码风格规范

### 2.1 导入顺序（严格）

所有文件必须以 from __future__ import annotations 开头。然后按以下顺序组织：

- 标准库导入（asyncio、logging、collections.abc、datetime 等）
- 第三方库导入（homeassistant 模块、bleak 等）
- 本地模块导入（使用相对导入，. 前缀）

### 2.2 类型注解（必须）

所有函数必须有返回类型注解。使用 PEP 604 语法表示可选类型（int | None 而非 Optional[int]）。集合类型使用内置泛型（list[str]、dict[str, int]、set[Callable[[], None]]）。属性也需要类型注解。

### 2.3 命名约定

| 类型 | 规则 | 示例 |
|------|------|------|
| 类名 | PascalCase | `AntiLossTagDevice`, `OptionsFlowHandler` |
| 函数/方法 | snake_case | `async_setup_entry`, `_async_write_bytes` |
| 私有成员 | _前缀 | `_client`, `_connected`, `_battery` |
| 常量 | UPPER_SNAKE_CASE | `DOMAIN`, `UUID_NOTIFY_FFE1` |
| 属性 | @property, 无下划线 | `available`, `connected`, `battery` |

### 2.4 异步编程模式

Home Assistant 集成方法必须是 async 函数。回调使用 callback 装饰器标记（非 async）。使用锁（async with）保护共享状态。任务创建使用 hass.async_create_task() 方法。

### 2.5 错误处理

捕获特定异常（如 BleakNotFoundError），使用 _LOGGER 记录错误。使用 try-except 结构作为安全网捕获多种异常。记录最后错误到实例变量（类型：str | None）供 UI 显示。

### 2.6 UUID 管理

所有 UUID 定义在 const.py，使用全小写字符串。命名格式：UUID_<SERVICE>_<CHARACTERISTIC> 或 UUID_SERVICE_<HEX>。

### 2.7 实体（Entity）模式

实体类通过类属性配置设备类、单位和状态类。构造函数接收设备实例和配置条目，设置实体名称和唯一 ID。使用 property 装饰器暴露状态值。

### 2.8 文档和注释

使用中文注释，英文变量和函数名。公开方法必须有 docstring（中文或英文）。使用注释分隔常量分组。

---

## 3. Home Assistant 特定规范

### Config Flow

Config Flow 类继承 config_entries.ConfigFlow，设置 VERSION 为 1。实现 async_step_bluetooth 方法处理蓝牙发现，设置唯一 ID 并检查是否已配置。OptionsFlowHandler 类继承 config_entries.OptionsFlow，实现 async_step_init 方法处理配置选项，使用 vol.Schema 定义验证规则。

### DeviceInfo

DeviceInfo 使用设备地址作为唯一标识符（identifiers 参数），设置设备名称、制造商和型号。

---

## 4. 架构模式

### 连接管理

BleConnectionManager 使用 asyncio.Semaphore 限制并发连接（全局连接槽位）。连接失败后使用指数退避策略（2 的 n 次方秒），避免连接风暴。使用 _connect_lock 保护连接操作，使用 _gatt_lock 保护 GATT 读写操作。槽位获取设置超时时间（如 20.0 秒），失败时计算退避时间（最小 30 秒）。

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

查看 Home Assistant 日志可使用 tail 命令跟踪日志文件并过滤 anti_loss_tag 相关内容。在 configuration.yaml 中配置 logger 部分启用调试日志，设置日志级别为 debug，可针对 custom_components.anti_loss_tag 和 bleak 组件启用。

---

**最后更新**: 2025-02-08  
**参考文档**: `docs/技术文档/开发规范.md`（详细中文规范）
