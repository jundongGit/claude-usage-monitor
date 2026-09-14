# Mac App Store 提交指南 — Usage Monitor for Claude

> 工程位置：`UsageMonitorMAS/`（Swift 重写版，v2.0.0）
> 打开方式：`open UsageMonitor.xcodeproj`（工程由 xcodegen 生成，改完 `project.yml` 后重新 `xcodegen generate`）

## 已完成（无需再动）

- ✅ Swift/AppKit 重写，功能与 Python 版 1:1：菜单栏用量显示、5h/7d/Sonnet 限额、
  今日 token/费用统计、cURL 一键配置、登录自启、超量通知
- ✅ App Sandbox 全开：`app-sandbox` + `network.client` + `user-selected.read-only` + `bookmarks.app-scope`
- ✅ `~/.claude` 目录通过 NSOpenPanel 授权 + security-scoped bookmark（沙盒合规）
- ✅ 登录自启改用 `SMAppService`（沙盒合规，替代 LaunchAgents + launchctl）
- ✅ 通知改用 `UserNotifications` 框架（替代已废弃的 NSUserNotification）
- ✅ Session cookie 存 Keychain（替代明文 JSON 文件）
- ✅ Info.plist：`LSApplicationCategoryType`（utilities）、`ITSAppUsesNonExemptEncryption=false`、
  `LSUIElement`、版权信息；最低系统 macOS 13.0
- ✅ Bundle ID：`nz.co.worldway.usagemonitor`，Team：HBCH66ZYGC（WORLDWIDE HOLIDAYS LIMITED）
- ✅ 隐私政策页：`website/privacy.html`（需部署，见下）

## 你需要做的事（按顺序）

### 1. 部署隐私政策（5 分钟）
把 `website/` 部署到 cloud01（用 `/deploy` skill），拿到 URL，例如
`https://usagemonitor.cloud01.top/privacy.html`。ASC 必填此项。

### 2. App Store Connect 创建应用
1. https://appstoreconnect.apple.com → 我的 App → ➕ 新建 App
2. 平台 macOS；名称 **Usage Monitor for Claude**（如被占用可加后缀）
3. Bundle ID：先去 https://developer.apple.com/account/resources/identifiers
   注册 `nz.co.worldway.usagemonitor`（⚠️ 注册后不可改，要换名趁现在）
4. SKU 随意（如 `usagemonitor2026`）；价格 **免费**；销售范围 **所有地区**

### 3. Xcode 归档上传（分发证书自动搞定）
1. Xcode 打开工程 → Settings → Accounts 确认已登录公司 Apple ID
2. Product → Destination 选 **Any Mac**，Product → **Archive**
3. Organizer → Distribute App → **App Store Connect** → Upload
   - Xcode 会自动创建缺失的 **Apple Distribution** / **Mac Installer Distribution**
     证书和 provisioning profile（你本机目前只有开发证书，这步会补齐）
4. 上传后在 ASC「TestFlight / 构建版本」等待处理完成（约 10–30 分钟）

### 4. ASC 元数据
| 项目 | 填什么 |
|---|---|
| 截图 | 1280×800 / 1440×900 / 2560×1600 / 2880×1800 任一尺寸，1–10 张。菜单栏应用建议截「菜单展开 + 桌面背景」全屏图再裁剪 |
| 描述 | 强调：菜单栏实时查看 Claude 用量、本地统计 token 成本、零数据收集 |
| 关键词 | claude,usage,monitor,token,menubar,ai 等 |
| 隐私政策 URL | 第 1 步部署的地址 |
| 支持 URL | 可用同一站点首页 |
| App 隐私标签 | 选 **「不收集数据」(Data Not Collected)** — 应用无服务器，凭据只存本地 Keychain，数据只发往用户自己的 claude.ai 账号 |
| 出口合规 | 已在 plist 声明豁免（仅 HTTPS），无需操作 |
| 年龄分级 | 4+ |

### 5. 审核备注（App Review Information）— 重要
审核员没有 Claude 账号，看不到真实数据。建议：
- 在「备注」里写明：*"This is a utility for users of Anthropic's Claude AI service to
  monitor their own account usage. It requires the user's own claude.ai session to display
  live data. Without configuration, the app shows a 'Not configured' state by design.
  All data stays on-device; see privacy policy."*
- 录一段 1–2 分钟演示视频（配置好后的真实效果），传到 ASC 的预览或附链接
- 不要在描述/截图里出现 Anthropic 官方 logo

## 审核风险提示（提前有数）

1. **5.2.2 第三方服务**：应用引导用户从 DevTools 复制 cookie 调 claude.ai 非公开接口。
   这是被拒概率最高的点，无技术规避手段。如被拒可申诉（强调：用户访问自己的数据、
   只读、零收集），或砍掉在线限额功能只保留本地统计（本地统计 100% 合规）。
2. **5.2.1 商标**："for Claude" 命名是行业惯例但不保证通过。如被拒，备选名:
   "AI Usage Monitor"、"TokenBar"。改显示名只需改 `project.yml` 里的
   `PRODUCT_NAME`/`CFBundleDisplayName`，Bundle ID 不用动。
3. **首次运行体验**：审核员会看到"Not configured"，务必写好审核备注（见上）。

## 与旧版的差异（告知老用户）

- 旧 Python 版配置文件 `~/.claude_usage_config.json` 在沙盒里不可读，
  老用户升级后需重新走一遍 cURL 配置（一步）
- 本地 token 统计需要首次手动授权 `~/.claude` 文件夹（菜单里点
  "Grant Access to Claude Code Data…"，面板会直接定位到该目录，点 Grant 即可）

## 日常维护

- 发新版本：改 `project.yml` 的 `MARKETING_VERSION`，`CURRENT_PROJECT_VERSION` +1，
  `xcodegen generate` → Archive → Upload
- 源码全部在 `Sources/`（8 个文件，约 700 行），无第三方依赖
