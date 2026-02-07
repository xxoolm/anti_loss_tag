# BLE 防丢标签集成 (Anti Loss Tag)

一个用于 Home Assistant 的 BLE 防丢标签自定义集成，支持远程控制、电量监控和按钮事件触发。

##  快速开始

### 功能特性

-  **双向连接**: 主动连接和保持连接模式
-  **实时监控**: RSSI 信号强度、连接状态、电池电量
-  **远程控制**: 铃声开关、防丢开关
 -  **按钮事件**: 捕捉标签按钮点击（事件类型："press"，数据包含原始十六进制）
-  **多设备支持**: 并发连接多个 BLE 标签
-  **智能重连**: 指数退避策略，避免连接风暴

### 安装

**HACS 安装（推荐）**:
1. HACS → 商店 → 搜索 "Anti Loss Tag" → 安装
2. 重启 Home Assistant

**手动安装**:
```bash
cp -r custom_components/anti_loss_tag ~/.homeassistant/custom_components/
```

### 配置

1. **设置** → **设备与服务** → **添加集成** → 搜索 "BLE 防丢标签"
2. 配置选项：
   - 维持连接：默认开启
   - 自动重连：默认开启
   - 断连报警：默认关闭
   - 电量轮询间隔：默认 **360 分钟**（6小时）

### 实体

集成会为每个设备创建：
- **传感器**：电量、信号强度、最后错误
- **二进制传感器**：已连接、在范围内、远离告警、防丢状态
- **按钮**：开始报警、停止报警
- **开关**：断连报警
- **事件**：按键事件（事件类型："press"，数据包含原始十六进制）

##  文档导航

| 文档 | 说明 | 链接 |
|------|------|------|
|  完整文档导航 | 按角色/主题查找 | [docs/索引.md](docs/索引.md) |
|  快速开始 | 详细安装和配置 | [docs/用户文档/快速开始.md](docs/用户文档/快速开始.md) |
|  配置指南 | 所有配置参数 | [docs/用户文档/配置指南.md](docs/用户文档/配置指南.md) |
|  自动化示例 | 自动化场景 | [docs/用户文档/自动化示例.md](docs/用户文档/自动化示例.md) |
|  故障排除 | 问题诊断 | [docs/用户文档/故障排除.md](docs/用户文档/故障排除.md) |
|  BLE 协议 | UUID 和协议 | [docs/技术文档/BLE协议规范.md](docs/技术文档/BLE协议规范.md) |
|  架构设计 | 系统架构 | [docs/技术文档/系统架构设计.md](docs/技术文档/系统架构设计.md) |
|  开发规范 | 代码规范 | [docs/技术文档/开发规范.md](docs/技术文档/开发规范.md) |
|  Python 代码审查 | 代码审查 | [docs/技术文档/Python代码审查.md](docs/技术文档/Python代码审查.md) |
|  KT6368A 硬件 | 硬件文档 | [docs/参考资料/KT6368A硬件文档.md](docs/参考资料/KT6368A硬件文档.md) |
|  KT6368A 固件 | 固件文档 | [docs/参考资料/KT6368A固件文档.md](docs/参考资料/KT6368A固件文档.md) |
|  Manifest 2025 | HA 标准 | [docs/参考资料/Manifest2025标准.md](docs/参考资料/Manifest2025标准.md) |
|  Java 代码审核 | Java 参考 | [docs/Java参考/Java代码审核.md](docs/Java参考/Java代码审核.md) |
|  Java 移植指南 | Java 参考 | [docs/Java参考/Java到Python移植指南.md](docs/Java参考/Java到Python移植指南.md) |

##  技术细节

**依赖项**:
- Home Assistant >= 2024.1.0
- bleak >= 0.21.0
- bleak-retry-connector >= 3.0.0

**支持设备**:
- 服务 UUID: `0000ffe0-0000-1000-8000-00805f9b34fb`
- 通知特征: `0000ffe1-0000-1000-8000-00805f9b34fb`

**项目结构**:
```
custom_components/anti_loss_tag/
├── __init__.py           # 集成入口
├── manifest.json         # 集成清单
├── const.py             # 常量定义
├── config_flow.py       # 配置流程
├── device.py            # 设备管理
├── connection_manager.py # 连接管理器
├── sensor.py            # 传感器实体
├── binary_sensor.py     # 二进制传感器实体
├── button.py            # 按钮实体
├── switch.py            # 开关实体
└── event.py             # 事件实体
```

##  开发

### 运行测试

```bash
# 安装测试依赖
pip install -r requirements-test.txt

# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/test_validation.py -v

# 运行特定测试
pytest tests/test_validation.py::test_is_valid_ble_address -v

# 查看测试覆盖率
pytest --cov=custom_components/anti_loss_tag --cov-report=html
```

### 代码质量检查

```bash
# 使用 ruff 进行代码检查（如果已安装）
ruff check custom_components/anti_loss_tag/

# 格式化代码
ruff format custom_components/anti_loss_tag/

# 类型检查（如果已安装 mypy）
mypy custom_components/anti_loss_tag/
```

### 本地开发

```bash
# 复制到 Home Assistant 自定义组件目录
cp -r custom_components/anti_loss_tag ~/.homeassistant/custom_components/

# 重启 Home Assistant 或重新加载配置
# 在 HA 中：配置 → 系统 → 服务器管理 → 重新加载核心 → YAML 配置重新加载
```

### 项目结构

```
custom_components/anti_loss_tag/
├── __init__.py              # 集成入口
├── manifest.json            # 集成清单
├── const.py                 # 常量定义
├── config_flow.py          # 配置流程
├── device.py               # 设备管理
├── connection_manager.py   # 连接管理器
├── sensor.py               # 传感器实体
├── binary_sensor.py        # 二进制传感器实体
├── button.py               # 按钮实体
├── switch.py               # 开关实体
├── event.py                # 事件实体
├── entity_mixin.py         # 实体混入基类
├── utils/                  # 工具模块
│   ├── __init__.py
│   ├── validation.py       # 输入验证
│   └── constants.py        # 常量定义
├── gatt_operations/        # GATT 操作模块
│   ├── __init__.py
│   ├── characteristic.py   # 特征操作
│   └── descriptors.py      # 描述符操作
└── archived/               # 归档的旧代码
    ├── coordinator.py      # 已弃用（使用 device.py 代替）
    ├── ble.py              # 已弃用（使用 device.py 代替）
    └── DEPRECATED.md       # 弃用说明
```

### 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范

本项目遵循以下代码规范：
- 所有文件必须以 `from __future__ import annotations` 开头
- 使用类型注解（PEP 604 语法）
- 使用 snake_case 命名函数和变量
- 使用 PascalCase 命名类
- 私有成员使用 `_` 前缀
- 常量使用 UPPER_SNAKE_CASE

详见 [AGENTS.md](AGENTS.md) 和 [docs/技术文档/开发规范.md](docs/技术文档/开发规范.md)

##  变更日志

### v1.1.0 (2025-02-08) - 代码质量改进

**改进**:
- 提取魔法数字为常量，提高可维护性
- 添加实体更新防抖动机制（1 秒），减少频繁更新
- 改进错误处理和资源清理
- 添加输入验证（BLE 地址、设备名称、电池电量）
- 修复 CancelledError 处理，符合 asyncio 最佳实践
- 改进连接槽位管理，防止资源泄漏

**新增**:
- 单元测试框架（pytest）
- 工具模块（`utils/validation.py`, `utils/constants.py`）
- GATT 操作模块
- 开发文档和测试文档

**归档**:
- `coordinator.py` 和 `ble.py` 已归档到 `archived/` 目录
- 功能已整合到 `device.py` 中

### v1.0.0 (2025-01-XX) - 初始版本

- 基本的 BLE 防丢标签集成功能
- 双向连接、实时监控、远程控制
- 按钮事件捕获
- 多设备支持

##  许可证

MIT License

##  链接

- GitHub: https://gitaa.com/MMMM/anti_loss_tag
- 问题反馈: https://gitaa.com/MMMM/anti_loss_tag/issues
