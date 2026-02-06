# BLE 防丢标签集成 (Anti Loss Tag)

一个用于 Home Assistant 的 BLE 防丢标签自定义集成，支持远程控制、电量监控和按钮事件触发。

## 功能特性

-  **双向连接**: 主动连接和保持连接模式
-  **实时监控**: RSSI 信号强度、连接状态、电池电量
-  **远程控制**: 铃声开关、防丢开关
-  **按钮事件**: 捕捉标签按钮点击事件（单击、双击、长按）
-  **多设备支持**: 并发连接多个 BLE 标签
-  **配置灵活**: 丰富的配置选项，可自定义轮询间隔、距离阈值等
-  **智能重连**: 指数退避策略，避免连接风暴

## 支持的设备

此集成支持使用以下 BLE 服务的防丢标签设备：

- **服务 UUID**: `0000ffe0-0000-1000-8000-00805f9b34fb`
- **通知特征**: `0000ffe1-0000-1000-8000-00805f9b34fb`

常见兼容设备包括市面上大多数基于 nRF51/nRF52 芯片的 BLE 防丢标签。

## 安装方法

### 通过 HACS 安装（推荐）

1. 在 HACS 中点击 "商店"
2. 搜索 "Anti Loss Tag"
3. 点击安装
4. 重启 Home Assistant

### 手动安装

1. 复制 `custom_components/anti_loss_tag` 目录到你的 Home Assistant 配置目录的 `custom_components` 文件夹
2. 重启 Home Assistant

```bash
cp -r custom_components/anti_loss_tag ~/.homeassistant/custom_components/
```

## 配置

### 添加设备

1. 在 Home Assistant 中进入 **设置** → **设备与服务**
2. 点击 **添加集成** → 搜索 "BLE 防丢标签"
3. 按照配对流程完成设备添加

### 配置选项

添加设备后，可以进入设备配置页面调整以下选项：

| 选项 | 默认值 | 说明 |
|------|--------|------|
| 维持连接 | 开启 | 是否保持与设备的持续连接 |
| 电量轮询间隔 | 60 分钟 | 电量读取间隔（5-10080 分钟） |
| RSSI 轮询间隔 | 5 分钟 | 信号强度读取间隔（1-60 分钟） |
| RSSI 阈值 | -80 dBm | 触发"远离"告警的信号强度阈值 |
| 超时阈值 | 30 秒 | 连接超时时间（5-120 秒） |

## 实体说明

集成会为每个设备创建以下实体：

### 传感器 (Sensor)

- **{设备名} 电量**: 设备电池电量（百分比）
- **{设备名} 信号强度**: RSSI 信号强度（dBm）
- **{设备名} 最后错误**: 最后一次错误信息（如有）

### 二进制传感器 (Binary Sensor)

- **{设备名} 连接状态**: 设备是否已连接
- **{设备名} 可用状态**: 设备是否可用（最近被发现）
- **{设备名} 远离告警**: 设备信号弱于阈值
- **{设备名} 防丢状态**: 防丢功能是否启用

### 按钮 (Button)

- **{设备名} 铃声开关**: 切换设备铃声
- **{设备名} 防丢开关**: 切换防丢功能

### 事件 (Event)

- **{设备名} 按钮事件**: 捕捉设备按钮事件
  - `single_click`: 单击
  - `double_click`: 双击
  - `long_press`: 长按

## 自动化示例

### 设备远离时发送通知

```yaml
automation:
  - alias: "标签远离提醒"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_tag_far_away
        to: "on"
    action:
      - service: notify.mobile_app_my_phone
        data:
          title: "防丢提醒"
          message: "标签 '我的钥匙' 已远离！"
```

### 双击按钮触发场景

```yaml
automation:
  - alias: "双击标签打开客厅灯"
    trigger:
      - platform: event
        event_type: anti_loss_tag_button_event
        event_data:
          device_id: "AA:BB:CC:DD:EE:FF"
          click_type: double_click
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
```

### 电量低时提醒

```yaml
automation:
  - alias: "标签电量低提醒"
    trigger:
      - platform: numeric_state
        entity_id: sensor.my_tag_battery
        below: 20
    action:
      - service: notify.mobile_app_my_phone
        data:
          title: "标签电量低"
          message: "标签 '我的钥匙' 电量仅剩 20%，请及时充电！"
```

## 故障排除

### 设备无法连接

1. 确认设备蓝牙已开启且在范围内
2. 检查 Home Assistant 的蓝牙适配器权限
3. 尝试重启 Home Assistant
4. 查看日志：**设置** → **系统** → **日志**

### 连接频繁断开

1. 增加 **超时阈值** 配置
2. 确认设备电量充足
3. 减少同时连接的 BLE 设备数量

### 电量/信号不更新

1. 检查 **维持连接** 选项是否开启
2. 调整 **轮询间隔** 设置
3. 确认设备支持相应的 BLE 特征

## 技术细节

### 依赖项

- Home Assistant >= 2024.1.0
- bleak >= 0.21.0
- bleak-retry-connector >= 3.0.0
- bluetooth_adapters (Home Assistant 内置)

### BLE 服务

| UUID | 说明 |
|------|------|
| `0000ffe0-0000-1000-8000-00805f9b34fb` | 主服务 |
| `0000ffe1-0000-1000-8000-00805f9b34fb` | 通知特征 |
| `0000180f-0000-1000-8000-00805f9b34fb` | 电池服务 |
| `00002a19-0000-1000-8000-00805f9b34fb` | 电量特征 |
| `00001802-0000-1000-8000-00805f9b34fb` | 即时报警服务 |
| `00002a06-0000-1000-8000-00805f9b34fb` | 报警级别特征 |

### 并发控制

集成使用全局连接管理器限制并发连接数，避免蓝牙适配器过载。连接失败后采用指数退避策略（2^n 秒），最多退避 30 秒。

## 开发

### 项目结构

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
└── requirements.txt     # Python 依赖
```

### 代码规范

请参考项目根目录的 `AGENTS.md` 文件了解详细的代码规范和开发指南。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 链接

- GitHub: https://gitaa.com/MMMM/anti_loss_tag
- 问题反馈: https://gitaa.com/MMMM/anti_loss_tag/issues

## 更新日志

### v1.0.0 (2025-02-06)

- 初始版本
- 支持基本的连接、控制和监控功能
- 支持按钮事件和自动化
