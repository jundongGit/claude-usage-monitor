#!/bin/bash
# 卸载开机自启动

echo "正在卸载 Claude Usage Monitor 开机自启动..."

PLIST_PATH=~/Library/LaunchAgents/com.claude.usage.monitor.plist

# 卸载服务
launchctl unload "$PLIST_PATH" 2>/dev/null

# 删除 plist 文件
rm "$PLIST_PATH" 2>/dev/null

echo "✅ 开机自启动已卸载"
