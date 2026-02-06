# manifest.json 2025 标准参考

> **Home Assistant 2025 年 manifest.json 最新要求**

## 一、必需字段

### 1.1 基础信息（所有集成必需）

```json
{
  "domain": "anti_loss_tag",
  "name": "Anti Loss Tag",
  "codeowners": ["@yourusername"],
  "documentation": "https://github.com/yourusername/anti_loss_tag",
  "requirements": ["bleak>=0.21.0", "bleak-retry-connector>=3.0.0"],
  "version": "1.0.0"
}
```

### 1.2 2025 新增必需字段

#### integration_type（必需）

**值与说明**：

| 值          | 说明                     | 适用场景                 |
| ----------- | ------------------------ | ------------------------ |
| `device`    | 提供单个设备             | ESPHome、ZHA、我们的项目 |
| `entity`    | 提供基本实体平台         | 传感器平台、天气预报     |
| `hardware`  | 硬件集成                 | RPi GPIO、串口           |
| `helper`    | 帮助实体                 | 重复器、模板组           |
| `hub`       | 集线器（多个设备/服务）   | Philips Hue、Z-Wave      |
| `service`   | 单个服务                 | 日志记录器               |
| `system`    | 系统集成                 | 上下文相关               |
| `virtual`   | 虚拟集成                 | 家庭组、区域             |

**我们的选择**：`"device"` - 每个防丢标签是独立设备

---

## 二、IoT 类别（iot_class）

### 2.1 类别对比

| 类别             | 说明                     | 何时使用                             |
| ---------------- | ------------------------ | ------------------------------------ |
| `local_polling`  | 直接通信，轮询状态       | 需要持续轮询才能获取状态（有延迟）   |
| `local_push`     | 直接通信，设备主动通知   | 设备主动推送状态变化（无延迟）       |
| `cloud_polling`  | 云API，轮询              | 通过云服务轮询（有延迟）             |
| `cloud_push`     | 云API，webhook           | 云服务主动推送（有延迟但更实时）     |

### 2.2 我们的选择：`local_push`

**理由**：
- 设备通过 FFE1 通知**主动推送**按钮事件（实时）
- 电量/RSSI 虽然需要轮询，但**核心事件是推送的**
- 符合"设备主动通知"的定义

**对比 `local_polling`**：
- `local_polling`：需要持续轮询才能获取状态，延迟高
- `local_push`：设备主动通知，延迟低

---

## 三、依赖项（dependencies）

### 3.1 标准依赖

```json
"dependencies": ["bluetooth_adapters"]
```

**用途**：
- 需要 BLE 扫描功能
- 需要 RSSI 监控
- 官方推荐的 BLE 集成最佳实践

### 3.2 可选依赖

```json
"dependencies": ["bluetooth_adapters", "usb"]
```

**何时添加 USB**：
- 如果集成需要访问 USB 设备
- 如果使用 USB 蓝牙适配器特定功能

---

## 四、配置流程（config_flow）

### 4.1 基础配置

```json
"config_flow": true
```

**含义**：
- 集成提供 UI 配置流程
- 用户通过 HACS/配置面板添加设备

### 4.2 配置流程要求

**必须实现**：
1. 步骤 1：显示配置表单
2. 步骤 2：扫描设备（5秒，FFE0 过滤）
3. 步骤 3：用户选择设备
4. 步骤 4：创建配置条目

---

## 五、版本号（version）

### 5.1 格式要求

**使用 AwesomeVersion 解析**：
- CalVer：`2025.01.01`
- SemVer：`1.0.0`
- SemVer with build：`1.0.0-build1`

**我们的选择**：`"1.0.0"`（SemVer）

### 5.2 发布与版本策略

**主版本（Major）**：不兼容的 API 变更
**次版本（Minor）**：向后兼容的功能新增
**修订版（Patch）**：向后兼容的问题修复

---

## 六、BLE 集成特殊要求

### 6.1 bluetooth 字段

```json
"bluetooth": [
  {
    "UUID": "0000FFE0-0000-1000-8000-00805F9B34FB",
    "connectable": true
  }
]
```

**说明**：
- `UUID`：服务 UUID（用于扫描过滤）
- `connectable`：是否可连接（true/false）

### 6.2 iot_class 选择建议

| 场景                         | 推荐类别        | 理由                           |
| ---------------------------- | --------------- | ------------------------------ |
| 设备主动推送事件（按钮等）   | `local_push`    | 实时性好                       |
| 需要轮询才能获取状态         | `local_polling` | 简单直接                       |
| 混合模式（推送+轮询）        | `local_push`    | 核心事件是推送的               |
| 通过云服务控制               | `cloud_polling` 或 `cloud_push` | 取决于API                    |

---

## 七、质量等级（Quality Scale）

### 7.1 Bronze 级别（最低要求）

**必须满足**：
-  有文档（README + 使用说明）
-  有配置流程（config_flow = true）
-  manifest.json 完整（所有必需字段）
-  基本错误处理
-  通过基本测试

**我们当前状态**：
-  完整文档（`docs/` 目录）
-  配置流程
-  manifest.json 完整
-  详细错误处理
-  代码审查（`docs/技术文档/Python代码审查.md`）

### 7.2 Silver 级别（推荐目标）

**额外要求**：
-  完整文档（安装、配置、自动化、故障排除）
-  类型注解（Type Hints）
-  单元测试（测试覆盖率 > 60%）
-  代码规范（Ruff/Mypy 通过）
-  持续维护（最近 6 个月有更新）

**我们的差距**：
-  单元测试（待添加）
-  测试覆盖率（待提升）

### 7.3 Gold 级别（最高标准）

**额外要求**：
-  完整测试套件（覆盖率 > 90%）
-  多语言支持（至少英语）
-  可扩展架构
-  持续集成（GitHub Actions）
-  社区活跃（Issue 响应 < 7 天）

---

## 八、完整示例

### 8.1 我们的 manifest.json

```json
{
  "domain": "anti_loss_tag",
  "name": "Anti Loss Tag",
  "codeowners": ["@yourusername"],
  "documentation": "https://github.com/yourusername/anti_loss_tag",
  "iot_class": "local_push",
  "requirements": [
    "bleak>=0.21.0",
    "bleak-retry-connector>=3.0.0"
  ],
  "dependencies": ["bluetooth_adapters"],
  "config_flow": true,
  "integration_type": "device",
  "version": "1.0.0",
  "bluetooth": [
    {
      "UUID": "0000FFE0-0000-1000-8000-00805F9B34FB",
      "connectable": true
    }
  ]
}
```

### 8.2 字段验证清单

-  `domain`：小写，无空格
-  `name`：简洁，用户友好
-  `codeowners`：至少一个 GitHub 用户名
-  `documentation`：有效的 HTTPS URL
-  `iot_class`：从列表中选择
-  `requirements`：使用版本约束（`>=` 或 `==`）
-  `dependencies`：标准集成名称
-  `config_flow`：true（提供UI配置）
-  `integration_type`：从列表中选择
-  `version`：有效的 CalVer/SemVer
-  `bluetooth`：正确的 UUID 格式

---

## 九、2025 新特性

### 9.1 integration_type（必需）

- 2025 新增字段
- 以前是可选的，现在是必需的
- 用于更好地区分集成类型

### 9.2 iot_class 细化

- 新增 `local_push` 类别
- 更准确地区分推送和轮询模式
- 推荐使用 `local_push` 而非 `local_polling`（如果适用）

### 9.3 Bluetooth 集成增强

- 2025.6+ 改进了蓝牙扫描
- 可视化蓝牙设备
- 更好的连接管理
- 推荐使用 `bleak-retry-connector`

---

## 十、常见问题

**Q: integration_type 和 iot_class 有什么区别？**

A: 
- `integration_type`：**集成架构类型**（device/hub/service等）
- `iot_class`：**设备通信方式**（local_push/local_polling等）

---

**Q: 为什么选择 local_push 而非 local_polling？**

A: 
- 设备主动推送按钮事件（实时）
- 即使电量需要轮询，**核心事件是推送的**
- `local_push` 更准确反映通信模式

---

**Q: 什么时候应该选择 hub 而非 device？**

A: 
- 如果集成管理**多个设备或服务**（如 Philips Hue），选 `hub`
- 如果集成提供**单个设备**（如 ESPHome），选 `device`
- 每个防丢标签是独立的，所以我们选 `device`

---

**Q: version 使用 CalVer 还是 SemVer？**

A: 
- CalVer（`2025.01.01`）：日历版本，适合时间敏感项目
- SemVer（`1.0.0`）：语义版本，适合功能驱动项目
- 推荐 SemVer（更通用）

---

**Q: 如何测试 manifest.json 是否正确？**

A: 
1. 使用 HA 的 manifest 验证工具
2. 检查 HA 日志中的 manifest 加载错误
3. 确保集成在 HA 中正常加载

---

## 十一、参考资源

- **Home Assistant 官方文档**：[Creating Integration Manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- **Integration Type 参考**：[Integration Types](https://developers.home-assistant.io/docs/creating_integration_manifest/#integration-type)
- **IoT Class 参考**：[IoT Classes](https://developers.home-assistant.io/docs/creating_integration_manifest/#iot-class)
- **Bluetooth 集成文档**：[Bluetooth](https://developers.home-assistant.io/docs/bluetooth/)
- **Quality Scale**：[Quality Scale](https://developers.home-assistant.io/docs/internationalization/quality/)

---

**相关文档**：
- **开发规范**：`docs/技术文档/开发规范.md`
- **架构设计**：`docs/技术文档/系统架构设计.md`
- **BLE 协议**：`docs/技术文档/BLE协议规范.md`
