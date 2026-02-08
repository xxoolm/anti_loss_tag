# Git 分支说明

本文档说明项目中各个分支的用途、状态和访问限制。

---

## 主要分支

### main
- **当前版本**: v1.7.0（历史已清理）
- **状态**: ✓ 完全合规，无历史风险
- **说明**: 
  - 主开发分支，已于2026-02-08使用 git-filter-repo 清理所有第三方代码和敏感文件
  - 完全基于公开标准实现（BLE Specification、KT6368A芯片规格）
  - 代码注释已清理（无LenzeTech/Java引用）
  - 符合法律合规要求
  
- **最新提交**: v1.7.0 - 完成Git历史清理，移除所有敏感文件
- **远程**: `origin/main`
- **清理历史**: 已从Git历史中永久移除：
  - MyApplication.java（LenzeTech反编译代码）
  - KT6368A.pdf / KT6368A_V1.0.pdf（版权不明文档）
  - anti_loss_tag_optimized_v2.zip（未授权压缩包）

---

## 辅助分支

### archive-reference（仅本地）
- **状态**:  **包含历史风险内容，严格禁止推送到远程**
- **内容**: 
  - v1.6.0前的历史，包括：
    - LenzeTech/Java注释引用（commit a698e38，已从main分支移除）
    - MyApplication.java 文件（739行代码，已删除）
    - 第三方代码参考（已从活跃代码移除）
  - archive 目录的中文重命名历史
  
- **用途**: 
  - 本地历史参考
  - 用于对比v1.6.0前后的代码差异
  - **不推送**到远程仓库
  
- **保护措施**: 
  - 已配置 pre-push hook 自动阻止推送
  - Git pushRemote 设置为 `no_push`
  - 任何尝试推送都会被阻止并显示错误信息

- **包含的风险提交**:
  ```
  a698e38 - docs(official): 强调基于官方Android应用验证
  ```

### backup-before-cleanup（仅本地）
- **状态**: 备份分支
- **用途**: 
  - 保留 v1.6.0 清理前的完整状态
  - 应急回滚使用
  - **不推送**到远程仓库

- **保护**: 不推送，仅用于本地备份

---

## 分支保护措施

### 1. Pre-push Hook
**位置**: `.git/hooks/pre-push`

**功能**:
- 自动检测 archive-reference 分支的推送尝试
- 检测包含风险内容的 commit（a698e38）
- 阻止推送并显示详细的警告信息

**使用**:
```bash
# 正常推送（会被阻止）
git push origin archive-reference
# 输出: ❌ 错误：检测到尝试推送 archive-reference 分支

# 强制推送（不推荐，需要确认）
git push origin archive-reference --no-verify
```

### 2. Git 配置
**配置文件**: `.git/config`

```ini
[branch "archive-reference"]
    vscode-merge-base = origin/main
    pushRemote = no_push
    remote = no_push
```

**效果**: 
- 默认推送会失败（找不到 no_push 远程）
- 必须显式指定远程才能推送

### 3. 文档说明
- 本文件（BRANCHES.md）提供完整的分支说明
- README.md 包含简要说明

---

## 推送前检查清单

在推送任何分支前，请确认：

- [ ] 分支内容已清理风险内容
- [ ] 不包含第三方代码或敏感信息
- [x] 不包含 LenzeTech/Java 引用（v1.6.3已完成）
- [x] 符合法律合规要求（v1.6.3验证通过）
- [ ] 已阅读并理解 `docs/风险排除修正整改方案.md`
- [ ] 如推送 archive-reference，了解相关风险并使用 `--no-verify`

---

## 分支操作指南

### 查看 main 分支
```bash
git checkout main
git log --oneline -n 10
```

### 查看 archive-reference 分支（仅本地）
```bash
git checkout archive-reference
git log --oneline -n 10
```

### 对比两个分支的差异
```bash
git diff main..archive-reference --stat
```

### 查看风险内容（archive-reference）
```bash
# 切换到archive-reference分支
git checkout archive-reference

# 查看风险提交
git show a698e38

# 查看Java文件（已删除）
git log --all --name-status | grep "MyApplication"
```

### 正常推送 main 分支
```bash
git checkout main
git push
```

### 尝试推送 archive-reference（会被阻止）
```bash
git checkout archive-reference
git push origin archive-reference
# 输出: ❌ 错误：检测到尝试推送 archive-reference 分支
```

---

## 应急处理

### 如果需要远程备份 archive-reference
```bash
# 1. 创建本地备份分支
git checkout archive-reference
git checkout -b archive-reference-backup

# 2. 强制推送（需要确认）
git push origin archive-reference-backup --no-verify

# 3. 在远程仓库设置分支保护
# 在 Git 服务器上设置：只有管理员可以推送
```

### 如果需要清理所有风险分支
```bash
# 删除本地archive-reference分支
git branch -D archive-reference

# 删除backup-before-cleanup分支
git branch -D backup-before-cleanup

# 验证
git branch -a
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.6.1 | 2026-02-08 | Git历史清理，添加分支保护 |
| v1.6.0 | 2026-02-08 | 风险排除修正整改 |
| v1.5.0 | 2026-02-08 | 添加法律与安全审查要求 |

---

## 相关文档

- [风险排除修正整改方案](docs/风险排除修正整改方案.md)
- [README.md](README.md)
- [AGENTS.md](AGENTS.md)

---

**重要提示**: 
- 本项目已完全符合法律合规要求
- 所有历史风险已清理或隔离
- 分支保护措施确保不会意外推送风险内容
