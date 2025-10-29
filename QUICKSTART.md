# 快速开始指南

## 📦 安装步骤

### 1. 安装依赖

```bash
cd "/Users/jundong/Documents/FREEAI/Dev/Claude usage"
pip3 install -r requirements.txt
```

### 2. 获取 Cookie

#### 方法1：完整 Cookie 字符串（推荐）

1. 打开 Chrome 浏览器
2. 登录 [Claude.ai](https://claude.ai)
3. 按 `F12` 打开开发者工具
4. 进入 **Application** 标签
5. 左侧选择 **Cookies** → `https://claude.ai`
6. 复制所有 Cookie 为如下格式：
   ```
   sessionKey=value1; __cf_bm=value2; intercom-id=value3; ...
   ```

#### 方法2：从 Network 请求获取（如果方法1不行）

1. 开发者工具中进入 **Network** 标签
2. 访问 `https://claude.ai/settings/usage`
3. 找到 `usage` 请求
4. 点击后查看 **Headers** → **Request Headers**
5. 找到 `Cookie:` 这一行，复制完整的值

### 3. 获取组织 ID

你的组织 ID 是:
```
314822f8-5b98-410e-a092-1ef999fe98a8
```

### 4. 运行应用

```bash
python3 main.py
```

### 5. 首次配置

1. 应用启动后，顶部状态栏会出现 **⚠️** 图标
2. 点击图标，选择 **⚙️ 设置 Cookie**
3. 粘贴你的 Cookie 字符串
4. 点击 OK
5. 粘贴组织 ID: `314822f8-5b98-410e-a092-1ef999fe98a8`
6. 点击 OK

应用会立即刷新并显示你的使用情况！

## 🎨 界面说明

### 状态栏图标

- **97%** - 当前 5 小时使用率
- **⚠️** - 未配置
- **🔒** - Cookie 已过期
- **❌** - 错误

### 菜单显示

```
📊 Claude 使用情况
━━━━━━━━━━━━━━━━━━━━━━
⏱️  5小时: 🔴 97% (重置: 2小时30分钟)
📅 7天: 🟡 51% (重置: 1天14小时)
💎 Opus: 🟢 0% (未使用)
━━━━━━━━━━━━━━━━━━━━━━
🔄 刷新
⚙️  设置 Cookie
━━━━━━━━━━━━━━━━━━━━━━
❌ 退出
```

### 颜色指示

- 🟢 **绿色** - 使用率 < 70%
- 🟡 **黄色** - 使用率 70-89%
- 🔴 **红色** - 使用率 ≥ 90%

## 🔔 通知

当 5 小时使用率达到 95% 时，会自动弹出通知提醒。

## 🔄 自动刷新

应用每 5 分钟自动刷新一次数据。

## ⚙️ 配置文件位置

```
~/.claude_usage_config.json
```

## 🐛 故障排除

### Cookie 过期了怎么办？

看到 🔒 图标时：
1. 重新登录 Claude.ai
2. 获取新的 Cookie
3. 点击 **⚙️ 设置 Cookie** 更新

### 应用无法启动？

检查是否安装了依赖：
```bash
pip3 install rumps requests
```

### 显示错误或无数据？

查看终端输出，会显示详细的错误信息和 API 返回的原始数据。

## 🚀 开机自启动（可选）

### 方法1：登录项

1. 创建启动脚本 `start_claude_monitor.command`:
   ```bash
   #!/bin/bash
   cd "/Users/jundong/Documents/FREEAI/Dev/Claude usage"
   python3 main.py
   ```

2. 添加执行权限:
   ```bash
   chmod +x start_claude_monitor.command
   ```

3. 系统偏好设置 → 用户与群组 → 登录项 → 添加此脚本

### 方法2：使用 Automator（推荐）

1. 打开 **Automator**
2. 新建 **应用程序**
3. 添加 **运行 Shell 脚本** 动作:
   ```bash
   cd "/Users/jundong/Documents/FREEAI/Dev/Claude usage"
   /usr/local/bin/python3 main.py
   ```
4. 保存为 `ClaudeMonitor.app`
5. 添加到登录项

## 💡 提示

- Cookie 通常 7-90 天过期，过期后需要重新设置
- 使用率达到 100% 后需要等待重置时间
- 可以手动点击刷新立即更新数据
