#!/bin/bash
# Git 初始化脚本
# 使用方法: bash init_git.sh

set -e

echo "正在初始化 Git 仓库..."

# 初始化 git 仓库
git init

# 添加远程仓库
git remote add origin https://gitaa.com/MMMM/anti_loss_tag.git

# 创建初始提交
git add .
git commit -m "feat: 初始化 BLE 防丢标签 Home Assistant 集成

- 添加完整的 Home Assistant 自定义集成代码
- 支持双向连接、电量监控、按钮事件
- 支持远程控制（铃声、防丢开关）
- 支持 RSSI 信号强度监控和远离告警
- 包含完整的文档和配置示例
- 符合 HACS 规范"

echo "Git 仓库初始化完成！"
echo "远程仓库: https://gitaa.com/MMMM/anti_loss_tag.git"
echo ""
echo "下一步："
echo "1. 检查状态: git status"
echo "2. 推送到远程: git push -u origin main"
echo "   或创建 main 分支: git checkout -b main"
