#!/bin/bash
# 安装开机自启动脚本

echo "正在安装 Claude Usage Monitor 开机自启动..."

# 确保 LaunchAgents 目录存在
mkdir -p ~/Library/LaunchAgents

# 复制 plist 文件（已经创建在正确位置）
PLIST_PATH=~/Library/LaunchAgents/com.claude.usage.monitor.plist

if [ -f "$PLIST_PATH" ]; then
    echo "✅ plist 文件已存在"
else
    echo "❌ 错误：plist 文件不存在"
    exit 1
fi

# 卸载旧的服务（如果存在）
launchctl unload "$PLIST_PATH" 2>/dev/null

# 加载新的服务
launchctl load "$PLIST_PATH"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 开机自启动安装成功！"
    echo ""
    echo "服务已启动，你可以："
    echo "  • 重启电脑测试自启动"
    echo "  • 查看日志: tail -f /tmp/claude-usage-monitor.log"
    echo ""
    echo "如需卸载自启动："
    echo "  launchctl unload ~/Library/LaunchAgents/com.claude.usage.monitor.plist"
    echo "  rm ~/Library/LaunchAgents/com.claude.usage.monitor.plist"
else
    echo "❌ 安装失败"
    exit 1
fi
