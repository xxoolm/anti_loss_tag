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

##  许可证

MIT License

##  链接

- GitHub: https://gitaa.com/MMMM/anti_loss_tag
- 问题反馈: https://gitaa.com/MMMM/anti_loss_tag/issues
