# 已弃用代码模块

本目录包含已从主代码库中移除的模块，保留用于历史参考。

## 模块列表

### ble.py

**弃用时间**：2025-02-08

**原功能**：实现了 `BleTagBle` 类，提供底层 GATT 操作封装

**替代方案**：所有功能已整合到 `custom_components/anti_loss_tag/device.py` 的 `AntiLossTagDevice` 类中

**迁移方法**：
- `BleTagBle.write_alert_level()` → `AntiLossTagDevice.async_start_alarm()` / `async_stop_alarm()`
- `BleTagBle.write_disconnect_alarm()` → `AntiLossTagDevice.async_set_disconnect_alarm_policy()`
- `BleTagBle.read_battery()` → `AntiLossTagDevice.async_read_battery()`

---

### coordinator.py

**弃用时间**：2025-02-08

**原功能**：实现了 `BleTagCoordinator` 类，使用 HA Coordinator 模式

**替代方案**：`custom_components/anti_loss_tag/device.py` 中的 `AntiLossTagDevice` 提供了更完整的实现

**迁移方法**：
- `BleTagCoordinator.async_refresh_battery()` → `AntiLossTagDevice.async_read_battery()`
- `BleTagCoordinator.data.online` → `AntiLossTagDevice.available`
- `BleTagCoordinator.data.battery` → `AntiLossTagDevice.battery`

---

## 弃用政策

根据 PEP 387 软弃用政策，这些代码将：
- 保留在 `archive/modules/` 目录中
- 不再维护，但不会删除
- 不影响现有功能
- 可供历史参考

---

## 相关文档

- [../../archive/DEPRECATED.md](../DEPRECATED.md) - 完整的弃用说明
- [../../custom_components/anti_loss_tag/device.py](../../custom_components/anti_loss_tag/device.py) - 当前实现
