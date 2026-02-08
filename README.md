# BLE 防丢标签集成 (Anti Loss Tag)

> **专门为KT6368A蓝牙芯片和定制固件适配的Home Assistant集成**

本集成是针对KT6368A芯片（双模蓝牙5.1 SoC）及其定制防丢固件的专门适配器，充分利用该芯片的FFE0/FFE1/FFE2自定义协议特性，实现完整的防丢标签功能。

##  快速开始

### 功能特性

**KT6368A芯片专用功能**：
-  **芯片适配**: 专为KT6368A双模蓝牙5.1芯片设计（SOP-8封装）
-  **协议支持**: 完整实现FFE0服务、FFE1通知、FFE2策略控制
-  **即时报警**: 使用标准Alert Level（2A06）实现立即响铃/停止
-  **断开策略**: 通过FFE2特征值同步断开报警策略到芯片

**系统集成功能**：
-  **双向连接**: 主动连接和保持连接模式
-  **实时监控**: RSSI 信号强度、连接状态、电池电量
-  **远程控制**: 铃声开关、防丢开关
-  **按钮事件**: 捕捉标签按钮点击（FFE1通知，事件类型："press"）
-  **多设备支持**: 并发连接多个 KT6368A 防丢标签
-  **智能重连**: 指数退避策略，避免连接风暴

### 硬件要求

本集成专门支持基于**KT6368A芯片**的BLE防丢标签设备：

**KT6368A芯片规格**：
- **芯片类型**：双模蓝牙纯数据芯片（BLE + SPP）
- **蓝牙版本**：Bluetooth V5.1
- **封装形式**：SOP-8超小尺寸
- **工作电压**：2.2V - 3.4V（推荐3.3V）
- **典型应用**：iBeacon防丢器、蓝牙遥控器、自拍杆

**固件协议要求**：
- 服务UUID：`0000FFE0-0000-1000-8000-00805F9B34FB`（用于设备识别）
- 通知特征：`0000FFE1-0000-1000-8000-00805F9B34FB`（按钮事件上报）
- 策略特征：`0000FFE2-0000-1000-8000-00805F9B34FB`（断开报警配置）
- 报警特征：`00002A06-0000-1000-8000-00805F9B34FB`（即时响铃控制）
- 电量特征：`00002A19-0000-1000-8000-00805F9B34FB`（电量读取）

### 安装

**HACS 安装（推荐）**:
1. HACS → 商店 → 搜索 "Anti Loss Tag" → 安装
2. 重启 Home Assistant

**手动安装**：

将 custom_components/anti_loss_tag 目录复制到 Home Assistant 的配置目录中的 custom_components 子目录，然后重启 Home Assistant。

### 配置

1. **设置** → **设备与服务** → **添加集成** → 搜索 "BLE 防丢标签"
2. 扫描并选择您的KT6368A防丢标签设备（服务UUID为FFE0）
3. 配置选项：
   - 维持连接：默认开启（适配KT6368A的低功耗特性）
   - 自动重连：默认开启（使用指数退避策略）
   - 断连报警：默认关闭（通过FFE2特征值同步到芯片）
   - 电量轮询间隔：默认 **360 分钟**（6小时，读取2A19特征值）

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

##  技术架构

### 系统边界与角色

本项目是专门为KT6368A芯片（双模蓝牙5.1 SoC）设计的Home Assistant集成，提供 BLE 防丢标签设备的管理功能。系统边界限定于单个 BLE 设备的连接、控制和状态监控。通过 Home Assistant 的实体系统暴露设备状态，支持自动化和用户交互。

### 组件划分

项目采用分层架构，主要包含以下层次：

- 集成层：处理 Home Assistant 生命周期管理（加载、卸载、配置更新）
- 设备层：管理单个 BLE 设备的连接、状态和 GATT 操作
- 实体层：将设备状态暴露为 Home Assistant 实体（传感器、按钮、开关、事件）
- 工具层：提供验证、常量和 GATT 操作辅助功能

### 运行形态

集成加载后创建设备实例，根据配置选项决定连接模式：

- 维持连接模式：设备始终保持连接，状态实时更新
- 按需连接模式：仅在需要时建立连接，操作完成后断开

支持被动重连（通过蓝牙事件触发）和主动重连（指数退避策略）。连接状态变化通过实体更新反映到 Home Assistant 界面。

### 主流程链路

1. Home Assistant 加载集成，调用 async_setup_entry
2. 创建全局 BLE 连接槽位管理器（最多 3 个并发连接）
3. 初始化设备实例，从配置条目读取地址和名称
4. 设置平台（传感器、二进制传感器、开关、按钮、事件）
5. 启动设备连接任务（如果配置为维持连接）
6. 处理蓝牙事件和状态变化
7. 更新实体状态并触发自动化

### 配置加载时机

- 初始配置：集成首次添加时通过 Config Flow 创建
- 运行时修改：通过 Options Flow 修改配置选项，立即应用

### 依赖作用点

- bleak：在设备连接、GATT 读写操作中使用
- bleak-retry-connector：在连接重试和槽位管理中使用
- bluetooth_adapters：在设备发现和连接中使用

### 扩展点

- 实体类型：可通过添加新平台扩展（需在 __init__.py 的 PLATFORMS 列表中注册）
- GATT 操作：可通过 gatt_operations 模块扩展特征值操作
- 验证规则：可通过 utils/validation.py 扩展输入验证

##  技术方向

### 技术定位

本项目是 Home Assistant 的本地设备集成，通过 BLE 协议与防丢标签设备通信。主要使用场景包括物品防丢、位置提醒和远程控制。设计目标是提供低延迟、低功耗、高可靠的设备管理方案。

### 稳定性与兼容策略

版本号遵循语义化版本规范（主版本.次版本.修订号）。向后兼容性通过 Config Flow 和 Options Flow 维护。已弃用模块（coordinator.py、ble.py）保留在 archived 目录但标记为弃用，未来版本可能移除（遵循 PEP 387 软弃用政策）。

### 工程化约束

- 代码风格：遵循 AGENTS.md 和 docs/技术文档/开发规范.md 中定义的规范
- 类型注解：所有函数必须包含返回类型注解，使用 PEP 604 语法
- 测试：使用 pytest 进行单元测试，目标覆盖率 80%
- 文档：关键变更必须同步更新 README.md 和 CHANGELOG.md

### 安全与权限边界

- 不处理用户敏感数据，仅管理设备连接和状态
- BLE 地址作为设备标识符存储在配置中
- 不建立网络连接，仅使用本地 BLE 通信
- 不写入文件系统，除 Home Assistant 日志外

### 可观测性口径

- 通过 Home Assistant 日志记录关键事件和错误（日志级别：INFO、WARNING、ERROR）
- 传感器实体暴露设备状态（电量、信号强度、连接状态）
- 最后错误信息通过"最后错误"传感器实体可见
- 支持调试模式（在 configuration.yaml 中设置日志级别为 debug）

##  一致性契约清单

为确保文档与代码的一致性，以下变更必须同步更新文档：

### 新增或修改配置项时

必须同步文档位置：docs/用户文档/配置指南.md 和 AGENTS.md

必须同步内容：
- 配置项名称、类型、默认值
- 取值约束和验证规则
- 配置来源（entry.data 或 entry.options）
- 覆盖顺序和生效时机
- 实现位置（文件路径和行号）

### 新增或修改实体类型时

必须同步文档位置：README.md（实体章节）

必须同步内容：
- 实体类型（传感器、二进制传感器、按钮、开关、事件）
- 实体列表和功能描述
- 注册位置（文件路径）

### 入口点或运行形态变化时

必须同步文档位置：README.md（技术架构章节）和 AGENTS.md

必须同步内容：
- 主流程链路
- 运行形态（连接模式）
- 组件划分

### 依赖或环境变化时

必须同步文档位置：README.md（技术细节章节）和 manifest.json

必须同步内容：
- 依赖名称和版本要求
- 用途说明（运行时/开发依赖）
- Home Assistant 最低版本要求

### 涉及 BLE 协议或外部规范变化时

必须同步文档位置：docs/技术文档/BLE 协议规范.md

必须重新核实：
- 与 Bluetooth SIG 官方规范对齐
- UUID 格式和特征值行为
- 写入方法（Write vs Write Without Response）
- 数据格式和取值范围
- 更新外部规范对齐清单

##  技术细节

**依赖项**：

运行时依赖：
- Home Assistant：版本 2024.1.0 或更高
- bleak：版本 0.21.0 或更高（BLE GATT 客户端库）
- bleak-retry-connector：版本 3.0.0 或更高（连接重试机制）
- bluetooth_adapters：Home Assistant 蓝牙适配器集成

开发依赖：
- pytest：版本 7.4.0 或更高（测试框架）
- pytest-cov：版本 4.1.0 或更高（测试覆盖率）
- pytest-homeassistant-custom-component：版本 0.13.0 或更高（HA 测试组件）

**支持设备**：

服务 UUID：0000ffe0-0000-1000-8000-00805f9b34fb

关键特征：
- 通知特征：0000ffe1-0000-1000-8000-00805f9b34fb（按钮事件上报）
- 写入特征：0000ffe2-0000-1000-8000-00805f9b34fb（断连报警配置）
- 报警级别特征：00002a06-0000-1000-8000-00805f9b34fb（即时报警控制）
- 电量特征：00002a19-0000-1000-8000-00805f9b34fb（电量读取）

**项目结构**：

完整的项目结构详见下面的"开发"章节中的"项目结构"部分，包括所有模块、工具目录和归档文件的说明。

##  开发

### 运行测试

使用 pytest 框架运行测试。首先通过 pip 安装 requirements-test.txt 中的测试依赖。运行测试时可以使用以下命令形式：

- 运行所有测试：直接执行 pytest\n- 运行单个测试文件：指定测试文件路径，使用 -v 参数显示详细输出\n- 运行特定测试：指定文件和测试函数名，使用双冒号分隔\n- 查看测试覆盖率：使用 --cov 参数指定覆盖率目标，使用 --cov-report 生成报告格式（如 html）

### 代码质量检查

使用 ruff 进行代码检查和格式化（如果已安装）。使用 mypy 进行类型检查（如果已安装）。检查目标为 custom_components/anti_loss_tag/ 目录。

### 本地开发

将 custom_components/anti_loss_tag 目录复制到 Home Assistant 的自定义组件目录。重启 Home Assistant 或通过界面重新加载核心配置（配置 → 系统 → 服务器管理 → 重新加载核心）。

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
