# 更新日志

本文档记录项目的重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [未发布]

### 计划中
- 增加集成测试（多设备高并发场景）
- 增加长期稳定性压测
- 优化蓝牙代理混合场景（本机适配器 + ESPHome 代理）

---

## [2.0.3] - 2026-02-09

### 新增
- 每设备优先级操作队列（串行执行写入/读电量/策略同步），降低并发 GATT 冲突概率。
- 连接状态细分与错误分类（`idle/scanning/connecting/discovering/ready/degraded/backoff` + classification/type）。
- 连接槽位可观测指标：`acquire_total`、`acquire_timeout`、`acquire_error`、`average_wait_ms`。
- 电量轮询自适应策略：前台报警优先，后台读取在拥塞时自动让路与动态延时。

### 修复
- 修复多设备高峰期按钮操作失败率偏高问题（统一在设备层重试，避免按钮层和设备层双重重试）。
- 修复电量实体长期 `unavailable` 问题：实体可用性与“首次采样为空值”解耦。
- 修复 diagnostics 字段不一致问题（连接管理器字段、配置键名、连接状态来源）。

### 文档
- 更新 `README.md` 项目状态与稳定性能力说明。
- 更新 `docs/用户文档/配置指南.md` 多设备与轮询建议。
- 更新 `docs/用户文档/故障排除.md`，新增基于 diagnostics 的定位路径。
- 更新 `docs/技术文档/系统架构设计.md`，补充当前实现的队列调度与状态机。

### 验证
- `ruff check custom_components/anti_loss_tag/` 通过。
- `ruff format --check custom_components/anti_loss_tag/` 通过。
- 本地 `pytest` 在当前环境受限（缺少 `homeassistant` 依赖）。

---

## [1.8.0] - 2026-02-09

### 新增
- 连接后初始化流水线（服务发现、通知启用、首次电量读取、策略同步）。
- 电量读取状态标记与节流日志。

### 修复
- 修复写入路径在无可用客户端时错误信息不完整问题。
- 修复按钮异常提示不友好问题，统一转换为可读的 Home Assistant 错误。

---

## [1.7.1] - 2026-02-08

### 文档
- 新增优化方案与开发经验文档。

---

## [1.7.0] - 2026-02-08

### 架构
- 完成旧版本架构对比与基础优化方案整理。
