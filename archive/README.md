# 归档目录

本目录包含项目开发过程中的历史文件、旧版本代码和参考文档。

> **注意**：这些文件仅供参考和历史追溯，不是项目运行所必需的。当前活跃的代码位于 `custom_components/anti_loss_tag/` 目录。

---

## 目录结构

### modules/ - 已弃用代码模块

包含已被新实现替代的旧代码模块：
- `ble.py` - 旧的 BLE 操作封装
- `coordinator.py` - 旧的 Coordinator 模式实现

详见：[modules/README.md](modules/README.md)

---

### reports/ - 审计与优化报告

包含项目审计、优化和文档改进过程中的报告：

#### reports/audit/ - 代码审计与优化
- `2026-02-06-code-audit-report.md` - 完整代码审计报告（571行）
- `2026-02-06-optimization-plan.md` - 优化计划（1103行）
- `2026-02-06-optimization-complete.md` - 优化完成报告（350行）
- `2026-02-06-optimization-execution-log.md` - 执行日志（14行）

#### reports/docs/ - 文档改进
- `2026-02-07-docs-fix-report.md` - 文档修复报告（238行）

---

### old_versions/ - 旧版本代码

包含历史版本的完整代码快照：

#### v1/ - 第一版集成
- 完整的 HA 集成代码
- 使用 Coordinator 模式
- 基础功能实现

#### v2/ - 第二版集成
- 优化后的实现
- 部分代码改进
- 过渡版本

**注意**：当前版本（v1.2.0+）位于 `custom_components/anti_loss_tag/`

---

### reference_docs/ - 硬件参考文档

KT6368A 芯片相关文档：
- `KT6368A 定制固件 通用 Python 开发文档.md` - Python 开发指南
- `KT6368A 硬件开发文档（SOP-8）.md` - 硬件设计指南

更多硬件文档请参考：`docs/参考资料/`

---

### temp_files/ - 临时文件

开发过程中产生的临时文件：
- `MyApplication.java` 和 `MyApplication$3.java` - Android 示例代码
- `init_git.sh` - Git 仓库初始化脚本
- `anti_loss_tag_optimized_v2.zip` - 临时备份文件

**注意**：这些文件无实际用途，仅供参考。

---

### translations/ - 旧版本翻译文件

包含历史版本的翻译文件：
- `zh-Hans.json` - 旧版本中文翻译（36行）

当前版本的翻译文件位于：`custom_components/anti_loss_tag/translations/`

---

## DEPRECATED.md

弃用模块说明文档，详细记录了：
- 弃用原因
- 迁移方法
- 替代方案

详见：[DEPRECATED.md](DEPRECATED.md)

---

## 维护说明

**添加新归档内容时**：
1. 选择合适的子目录（modules/reports/old_versions/reference_docs/temp_files）
2. 添加相应的 README.md 说明
3. 更新本目录的索引

**清理规则**：
- 保留所有历史版本代码（v1, v2, ...）
- 保留所有审计和优化报告
- 临时文件可定期清理（但保留至少 6 个月）
