# 已归档模块说明

## 归档时间
2025-02-08

## 归档原因

这些模块是早期的 BLE 操作封装，功能已被 `device.py` 中的 `AntiLossTagDevice` 完全替代。

### archived/ble.py

- **原功能**: 实现了 `BleTagBle` 类，提供底层 GATT 操作封装
- **替代方案**: 所有功能已整合到 `device.py` 的 `AntiLossTagDevice` 类中
- **迁移方法**: 
  - `BleTagBle.write_alert_level()` → `AntiLossTagDevice.async_start_alarm()` / `async_stop_alarm()`
  - `BleTagBle.write_disconnect_alarm()` → `AntiLossTagDevice.async_set_disconnect_alarm_policy()`
  - `BleTagBle.read_battery()` → `AntiLossTagDevice.async_read_battery()`

### archived/coordinator.py

- **原功能**: 实现了 `BleTagCoordinator` 类，使用 HA Coordinator 模式
- **替代方案**: `device.py` 中的 `AntiLossTagDevice` 提供了更完整的实现
- **迁移方法**:
  - `BleTagCoordinator.async_refresh_battery()` → `AntiLossTagDevice.async_read_battery()`
  - `BleTagCoordinator.data.online` → `AntiLossTagDevice.available`
  - `BleTagCoordinator.data.battery` → `AntiLossTagDevice.battery`

## 弃用政策

根据 [PEP 387](https://peps.python.org/pep-0387/) 软弃用政策，这些代码将：

-  保留在 `archived/` 目录中
-  不再维护，但不会删除
-  不影响现有功能
-  可供历史参考

## 当前状态

- 原 `ble.py` 和 `coordinator.py` 文件仍保留在根目录
- 这些文件已标记为 **弃用**
- 新代码应使用 `device.py` 中的 `AntiLossTagDevice` 类
- 旧文件保留是为了向后兼容（如果外部有引用）

## 迁移指南

如果你需要使用这些模块中的特定功能，请参考 `device.py` 中的实现。

详细的迁移指南请参阅项目根目录的 `MIGRATION_GUIDE.md`（将创建）。

## 相关文档

- [REFACTORING_PLAN.md](../../REFACTORING_PLAN.md) - 整改方案
- [CODE_REVIEW_REPORT.md](../../CODE_REVIEW_REPORT.md) - 代码审查报告
- [MIGRATION_GUIDE.md](../../MIGRATION_GUIDE.md) - 迁移指南（待创建）
