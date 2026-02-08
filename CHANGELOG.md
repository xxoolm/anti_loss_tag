# 变更日志 (CHANGELOG)

本文档记录项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [未发布]

### 计划中
- 添加集成测试
- 性能基准测试
- 支持更多 BLE 设备型号

---

## [2.0.2] - 2026-02-09

### 修复（Critical Bug）

#### device.py - 修复 get_services() 方法不存在的错误

- **第 541 行**（async_read_battery）：
  - 修改前：`await client.get_services()`
  - 修改后：`_ = client.services`（访问属性触发服务发现）

- **第 806-809 行**（_async_write_bytes）：
  - 修改前：`await client.get_services()`
  - 修改后：`_ = client.services` + `self._cached_chars.clear()`

**根本原因**：
- 根据 bleak >= 0.21.0 官方文档，`get_services()` 方法已被移除
- `services` 是 property（属性），不需要 await 调用
- Home Assistant 的 `HaBleakClientWithServiceCache` 也无此方法
- 修复导致所有蓝牙通信功能完全失效的 AttributeError

**错误消息**：
```
无法执行动作"button/press" 
'HackBleakClientWithServiceCache' object has no attribute 'get_services'
```

---

## [2.0.0] - 2026-02-09

### 新增（Phase 3 完成）

#### 诊断功能
- 实现完整的 diagnostics 支持（按 HA IQS 规则）
  - `async_get_config_entry_diagnostics()`
  - `async_get_device_diagnostics()`
  - 包含设备状态、连接状态、实体信息等完整诊断
  - 脱敏敏感信息（BLE 地址仅显示前 6 位）

#### 测试增强
- `tests/test_multi_device_concurrency.py`（237 行）
  - 多设备并发操作测试
  - 连接池管理测试
  - 压力场景测试
- `tests/test_long_term_stability.py`（205 行）
  - 长期运行稳定性测试
  - 资源管理测试

#### 文档完善
- `docs/KNOWN_LIMITATIONS.md`（262 行）
  - 技术限制、功能限制、性能限制、兼容性限制
  - 操作系统差异（Linux/Windows/macOS）
  - 未来改进方向
- `docs/TROUBLESHOOTING.md`（387 行）
  - 设备连接问题、报警功能问题、电量显示问题
  - 实体状态问题、性能问题
  - 日志诊断方法、获取帮助
- `docs/DATA_UPDATE.md`（368 行）
  - 数据源、更新触发机制、更新频率
  - 缓存机制、性能考虑、数据一致性保证

---

## [1.10.0] - 2026-02-09

### 新增（Phase 2 完成）

#### Home Assistant 质量规则对齐

1. **PARALLEL_UPDATES 声明**
   - sensor/binary_sensor: `PARALLEL_UPDATES = 0`（读类，集中更新）
   - button/switch/event: `PARALLEL_UPDATES = 1`（动作类，限制并发）

2. **可用性状态单入口管理**
   - 新增 `_update_availability(available: bool)` 方法
   - 统一管理 `_available` 状态变更
   - 消除"假在线"风险

3. **runtime_data 规范**
   - 确认设备实例存入 `ConfigEntry.runtime_data`（符合 IQS）
   - 确认全局连接管理器存入 `hass.data`（明确共享语义）

#### 新增测试
- `tests/test_parallel_updates_and_availability.py`（245 行）
- `tests/test_runtime_data_usage.py`（187 行）

---

## [1.9.0] / [1.8.0] - 2026-02-09

### 新增（Phase 1 完成）

#### 错误降级优化
1. **统一同 UUID 多特征降级逻辑**
   - 新增 `_async_gatt_operation_with_uuid_fallback()` 方法
   - 统一处理 UUID 操作失败时的降级逻辑
   - 在 `async_read_battery` 和 `_async_write_bytes` 中复用

2. **对齐 log-when-unavailable 规则**
   - 添加 `_unavailability_logged` 状态位
   - 断连时仅记录一次不可用日志
   - 恢复时记录恢复日志并重置标志

3. **断连写入单次重连防护**
   - 确认 `_async_write_bytes` 已实现单次重连逻辑
   - 所有写入入口都通过统一通道

#### Bug 修复
- **多特征 UUID 错误消息匹配**：中文 → 英文
  - 修改前：`"该 UUID 对应多个特征"`
  - 修改后：`"Multiple Characteristics with this UUID"`

- **服务刷新方式**：`_services = client.services` → `await client.get_services()`
  -  注意：此修复在 v2.0.2 中被纠正

#### 新增测试
- `tests/test_device_ble_operations.py`（282 行）
- `tests/test_config_flow_validation.py`（165 行）

---

## [1.7.1] - 2026-02-08

### 文档
- 新增 `optimization_plan.md`：全面优化方案（v2.1.0）
  - 基于官方文档审校
  - 对齐 HA IQS 规则
  - 详细代码位置和关键点

---

## [1.7.0] - 2026-02-08

### 架构对比
- 老旧版本 v1.0.0 架构对比完成
- 当前版本架构优势确认
- 优化方案制定

---

## 版本命名规则

- **主版本**：重大架构变更（v1.x → v2.x）
- **次版本**：功能阶段完成（v2.0 → v2.1）
- **修订版本**：Bug 修复和小改进（v2.0.0 → v2.0.1）
- **紧急修复**：可跳过版本号（v2.0.0 → v2.0.2）

---

## 相关链接

- [优化方案](optimization_plan.md)
- [开发经验总结](DEVELOPMENT_LESSONS.md)
- [已知限制](docs/KNOWN_LIMITATIONS.md)
- [故障排查指南](docs/TROUBLESHOOTING.md)
- [数据更新机制](docs/DATA_UPDATE.md)
