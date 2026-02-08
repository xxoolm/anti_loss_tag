# Git 分支说明

本文档说明项目中各个分支的用途、状态和访问限制。

---

## 主要分支

### main
- **当前版本**: v1.7.0
- **状态**: ✓ 稳定版本
- **说明**: 
  - 主开发分支
  - 基于BLE Specification和KT6368A芯片规格实现
  
- **最新提交**: v1.7.0 - 文档和分支整理
- **远程**: `origin/main`

---

## 辅助分支

### archive-reference（仅本地）
- **内容**: 
  - archive 目录的重命名和整理工作
  - 从v1.3.0分叉
  
- **用途**: 
  - 本地开发参考
  - **不推送**到远程仓库
  
- **保护措施**: 
  - pre-push hook 自动阻止推送
  - Git pushRemote 设置为 `no_push`

---

## 分支保护措施

### 1. Pre-push Hook
**位置**: `.git/hooks/pre-push`

**功能**:
- 自动检测 archive-reference 分支的推送尝试
- 阻止推送并显示详细的警告信息
- 防止意外推送archive开发分支

**使用**:
```bash
# 正常推送（会被阻止）
git push origin archive-reference
# 输出: ❌ 错误：检测到尝试推送 archive-reference 分支

# 强制推送（如需）
git push origin archive-reference --no-verify
```

**注意**: archive-reference为仅本地开发分支，不应推送。

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

---

## 推送前检查清单

在推送任何分支前，请确认：

- [ ] 代码已测试
- [ ] 文档已更新
- [ ] 理解archive-reference为仅本地开发分支

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

### 正常推送 main 分支
```bash
git checkout main
git push
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.7.0 | 2026-02-08 | 文档和分支整理 |
| v1.6.0 | 2026-02-08 | 完整功能实现 |

---

## 相关文档

- [风险排除修正整改方案](docs/风险排除修正整改方案.md)
- [README.md](README.md)
- [AGENTS.md](AGENTS.md)
- [SECURITY.md](SECURITY.md)

---


