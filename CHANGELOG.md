# 变更日志 (CHANGELOG)

本文档记录项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 计划中
- 添加更多单元测试
- 添加集成测试
- 性能基准测试
- 支持更多 BLE 设备型号

---

## [1.6.9] - 2026-02-09

### 修复（致命错误）
- **device.py**: 修复 BleakClient API 不匹配问题
  - 第 517 行：`await client.get_services()` → `client.services`
  - 第 746 行：`await client.get_services()` → `client.services`
  - 第 813 行：`await client.get_services()` → `client.services`
  - 根据 bleak >= 0.21.0 官方文档，`get_services()` 方法已被移除
  - `services` 是 property（属性），不需要 await 调用
  - 修复导致所有蓝牙通信功能完全失效的 AttributeError

### 修复（用户体验）
- **config_flow.py**: 添加翻译占位符支持
  - 第 81 行：添加 `description_placeholders` 参数
  - 提供设备名称和 MAC 地址占位符的值
  - 修复前端翻译字符串格式化错误（MISSING_VALUE）

### 改进
- **代码质量**: 删除未使用的导入（asyncio、MIN_CONNECT_BACKOFF_SECONDS、DEFAULT_BLEAK_TIMEOUT）
- **代码规范**: 使用 `_services` 变量名表示故意的未使用变量

### 修复（版本同步）
- **manifest.json**: 更新版本号从 1.6.7 到 1.6.9
- **pyproject.toml**: 更新版本号从 1.4.0 到 1.6.9
- **配置修复**: 移除 pyproject.toml 中重复的 `[tool.coverage.run]` 和 `[tool.coverage.report]` 键

### 技术细节
- 参考 bleak 官方 API 文档：https://bleak.readthedocs.io/en/latest/api/client.html
- 参考 Home Assistant 翻译文档：https://developers.home-assistant.io/docs/internationalization/core/
- 所有代码通过 ruff 检查和格式化

---

## [1.4.0] - 2025-02-08

### 修复
- **manifest.json**: 添加缺失的 `domain` 字段，修复 HACS 验证失败问题
- **版本一致性**: 统一所有文档和代码中的版本号

### 改进
- **项目标准化**: 完善 `pyproject.toml`，添加 PEP 621 标准的 [project] section
- **依赖管理**: 创建 `requirements.txt`，明确项目依赖
- **文档对齐**: 统一 UUID 格式和版本号引用

---

## [1.3.0] - 2025-02-08

### 新增
- **完整测试套件**: 扩展单元测试覆盖
  - GATT 操作测试
  - 设备管理测试
  - 配置流程测试

### 改进
- **错误处理**: 增强异常处理和错误日志
- **代码质量**: 应用所有开发规范要求

---

## [1.2.0] - 2025-02-08

### 新增
- **工具模块完善**: 完成 utils/validation.py 和 utils/constants.py
- **GATT 操作模块**: 添加 gatt_operations/ 目录结构

### 改进
- **代码重构**: 提取重复代码，提高可维护性
- **文档完善**: 更新技术文档和用户指南

---

## [1.1.0] - 2025-02-08

### 新增
- **测试框架**: 添加 pytest 测试基础设施
  - 单元测试模板（`tests/test_validation.py`, `tests/test_constants.py`）
  - pytest 配置（`pyproject.toml`）
  - 测试依赖文件（`requirements-test.txt`）
  - 测试夹具（`tests/conftest.py`）

- **工具模块**: 创建 `utils/` 目录
  - `utils/validation.py` - 输入验证函数
    - BLE 地址格式验证
    - 设备名称验证
    - GATT handle 验证
    - 电池电量验证
  - `utils/constants.py` - 常量定义
    - 轮询间隔常量
    - 退避时间常量
    - 防抖动时间常量
    - 超时时间常量

- **GATT 操作模块**: 创建 `gatt_operations/` 目录
  - `gatt_operations/characteristic.py` - GATT 特征操作
  - `gatt_operations/descriptors.py` - GATT 描述符操作

- **代码文档**:
  - `AGENTS.md` - AI 编码助手指南
  - `docs/阶段1完成总结.md` - 代码归档总结
  - `docs/阶段2完成总结.md` - 关键问题修复总结
  - `docs/阶段3完成总结.md` - 代码质量改进总结

### 改进
- **代码质量**: 提取魔法数字为常量
  - 替换硬编码数字为命名常量
  - 提高代码可读性和可维护性
  - 便于统一修改配置

- **性能优化**: 添加实体更新防抖动
  - 实现 1 秒防抖动机制
  - 减少频繁更新导致的性能问题
  - 预期减少 50-90% 的数据库写入

- **错误处理**: 改进异常处理
  - 修复 `CancelledError` 处理（重新抛出异常）
  - 改进 `_on_disconnect` 错误处理（添加 try/finally）
  - 改进 `_release_connection_slot_soon`（添加异常处理）
  - 防止资源泄漏

- **输入验证**: 添加配置验证
  - BLE 地址格式验证（支持 XX:XX:XX:XX:XX:XX 和 XX-XX-XX-XX-XX-XX）
  - 设备名称验证（长度、控制字符检查）
  - 配置流程中集成验证
  - 友好的错误提示

- **代码组织**: 归档冗余代码
  - 将 `coordinator.py` 和 `ble.py` 归档到 `archived/` 目录
  - 在原文件中添加弃用警告
  - 创建 `archived/DEPRECATED.md` 说明文档
  - 遵循 PEP 387 软弃用政策

### 修复
- 修复 `_apply_connect_backoff()` 方法的缩进错误
- 删除重复代码块
- 修复潜在的槽位泄漏问题

### 文档
- 更新 `README.md`，添加开发文档
- 添加测试运行说明
- 添加代码质量检查说明
- 添加项目结构说明

### 技术细节
- 所有修改基于业界最佳实践
- 参考官方文档和标准：
  - PEP 387 (软弃用)
  - asyncio 官方文档
  - Home Assistant 开发者文档
  - bleak-retry-connector 最佳实践

---

## [1.0.0] - 2025-01-XX

### 新增
- **初始版本发布**
  - Home Assistant BLE 防丢标签集成
  - 支持双向连接模式
  - 实时监控（RSSI、连接状态、电池电量）
  - 远程控制（铃声开关、防丢开关）
  - 按钮事件捕获
  - 多设备支持
  - 智能重连（指数退避策略）

### 功能特性
- **传感器**: 电量、信号强度、最后错误
- **二进制传感器**: 已连接、在范围内、远离告警、防丢状态
- **按钮**: 开始报警、停止报警
- **开关**: 断连报警
- **事件**: 按键事件

### 技术栈
- Home Assistant >= 2024.1.0
- bleak >= 0.21.0
- bleak-retry-connector >= 3.0.0

### 支持设备
- 服务 UUID: `0000ffe0-0000-1000-8000-00805f9b34fb`
- 通知特征: `0000ffe1-0000-1000-8000-00805f9b34fb`

---

## 版本说明

### 版本号格式
- **主版本号**: 不兼容的 API 修改
- **次版本号**: 向下兼容的功能新增
- **修订号**: 向下兼容的问题修正

### 变更类型
- **新增**: 新功能
- **改进**: 现有功能的改进
- **修复**: 问题修复
- **变更**: 向下兼容的变更
- **弃用**: 即将移除的功能
- **移除**: 已移除的功能
- **安全**: 安全相关的修复或改进

---

## 升级指南

### 从 v1.0.0 升级到 v1.1.0

**兼容性**: 完全兼容，无需修改配置

**建议操作**:
1. 备份 Home Assistant 配置
2. 更新集成到最新版本
3. （可选）运行测试验证功能：`pytest`
4. （可选）检查日志确认无错误

**注意事项**:
- `coordinator.py` 和 `ble.py` 已弃用，但仍然可用
- 未来版本可能移除这些文件
- 建议新代码使用 `device.py` 中的 `AntiLossTagDevice`

---

## 未来计划

### v1.2.0 (计划中)
- [ ] 添加更多单元测试（目标覆盖率 80%）
- [ ] 添加集成测试
- [ ] 性能基准测试
- [ ] 支持更多 BLE 设备型号

### v1.3.0 (计划中)
- [ ] 可配置的防抖动时间
- [ ] 性能指标监控
- [ ] 高级自动化场景

### v2.0.0 (远期计划)
- [ ] 重构为异步架构
- [ ] 支持自定义 GATT 操作
- [ ] 插件系统

---

## 链接

- [GitHub Repository](https://github.com/xxoolm/anti_loss_tag)
- [Issue Tracker](https://github.com/xxoolm/anti_loss_tag/issues)
- [文档索引](docs/索引.md)

---

[未发布]: https://github.com/xxoolm/anti_loss_tag/compare/v1.6.9...HEAD
[1.6.9]: https://github.com/xxoolm/anti_loss_tag/compare/v1.6.8...v1.6.9
[1.4.0]: https://github.com/xxoolm/anti_loss_tag/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/xxoolm/anti_loss_tag/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/xxoolm/anti_loss_tag/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/xxoolm/anti_loss_tag/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/xxoolm/anti_loss_tag/releases/tag/v1.0.0
