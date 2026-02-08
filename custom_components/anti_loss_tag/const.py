from __future__ import annotations

DOMAIN = "anti_loss_tag"

CONF_ADDRESS = "address"
CONF_NAME = "name"

# Options
CONF_ALARM_ON_DISCONNECT = "alarm_on_disconnect"
CONF_MAINTAIN_CONNECTION = "maintain_connection"
CONF_AUTO_RECONNECT = "auto_reconnect"
CONF_BATTERY_POLL_INTERVAL_MIN = "battery_poll_interval_min"

DEFAULT_ALARM_ON_DISCONNECT = False
DEFAULT_MAINTAIN_CONNECTION = True
DEFAULT_AUTO_RECONNECT = True
DEFAULT_BATTERY_POLL_INTERVAL_MIN = 360  # 6 hours

# ============================================================================
# KT6368A 芯片专用协议定义
# ============================================================================
# 本集成专门为KT6368A双模蓝牙5.1 SoC（SOP-8封装）设计
#
# 官方参考实现：
# - 官方Android应用：iSearching Two（LenzeTech）
# - Java源码：MyApplication.java (526行) + MyApplication$3.java (213行)
# - 代码位置：archive/temp_files/（官方反编译代码）
#
# KT6368A定制协议（FFE0服务）- 官方实现验证：
# - FFE0: 服务UUID（设备扫描和识别）
# - FFE1: 通知特征（按键事件上报，字节流格式）
# - FFE2: 写入特征（断开报警策略，0x01=启用，0x00=关闭）
#
# 标准Bluetooth SIG UUID（在KT6368A固件中实现）：
# - 2A06: Alert Level（即时报警级别，Write Without Response）
# - 2A19: Battery Level（电量百分比，Read）
#
# 参考文档：
# - docs/Java参考/Java代码审核.md（官方Java代码架构分析）
# - docs/Java参考/Java到Python移植指南.md（Python实现指南）
# - docs/参考资料/KT6368A硬件文档.md
# - docs/参考资料/KT6368A固件文档.md
# ============================================================================

# BLE UUIDs (lowercase) - KT6368A芯片专用（官方验证）
UUID_SERVICE_FILTER_FFE0 = "0000ffe0-0000-1000-8000-00805f9b34fb"
UUID_NOTIFY_FFE1 = "0000ffe1-0000-1000-8000-00805f9b34fb"
UUID_WRITE_FFE2 = "0000ffe2-0000-1000-8000-00805f9b34fb"
UUID_ALERT_LEVEL_2A06 = "00002a06-0000-1000-8000-00805f9b34fb"
UUID_BATTERY_LEVEL_2A19 = "00002a19-0000-1000-8000-00805f9b34fb"

# Compatibility aliases used by coordinator.py / ble.py
SERVICE_UUID_FFE0 = UUID_SERVICE_FILTER_FFE0
CHAR_ALERT_LEVEL_2A06 = UUID_ALERT_LEVEL_2A06
CHAR_WRITE_FFE2 = UUID_WRITE_FFE2
CHAR_BATTERY_2A19 = UUID_BATTERY_LEVEL_2A19
DEFAULT_ONLINE_TIMEOUT_SECONDS = 30
DEFAULT_BATTERY_CACHE_SECONDS = 6 * 60 * 60
