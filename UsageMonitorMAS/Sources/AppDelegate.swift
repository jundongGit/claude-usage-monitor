import AppKit
import UserNotifications

final class AppDelegate: NSObject, NSApplicationDelegate {

    private let appVersion = Bundle.main.object(
        forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "?"

    private var statusItem: NSStatusItem!
    private var refreshTimer: Timer?
    private var lastNotificationTime: [String: TimeInterval] = [:]

    // MARK: - Menu items

    private let fiveHourItem = NSMenuItem(title: "⏱️  5-Hour: Loading...", action: nil, keyEquivalent: "")
    private let allModelsItem = NSMenuItem(title: "🛠️  All Models: Loading...", action: nil, keyEquivalent: "")
    private let sonnetItem = NSMenuItem(title: "🔷 Sonnet only: Loading...", action: nil, keyEquivalent: "")
    private let todayItem = NSMenuItem(title: "📈 Today: Loading...", action: nil, keyEquivalent: "")
    private let inputItem = NSMenuItem(title: "    ⬇️  Input: ...", action: nil, keyEquivalent: "")
    private let outputItem = NSMenuItem(title: "    ⬆️  Output: ...", action: nil, keyEquivalent: "")
    private let costItem = NSMenuItem(title: "💰 Cost: Loading...", action: nil, keyEquivalent: "")
    private let grantAccessItem = NSMenuItem(title: "📂 Grant Access to Claude Code Data…",
                                             action: #selector(grantFolderAccess), keyEquivalent: "")
    private let autostartItem = NSMenuItem(title: "🚀 Launch at Login",
                                           action: #selector(toggleAutostart), keyEquivalent: "")

    // MARK: - Lifecycle

    func applicationDidFinishLaunching(_ notification: Notification) {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem.button?.title = "…"

        setupMenu()
        setupEditMenu()
        updateAutostartMenu()
        Notifier.requestAuthorization()

        let config = ConfigStore.shared
        if config.cookie.isEmpty && config.orgId.isEmpty {
            showWelcomeGuide()
        }

        refresh()
        refreshTimer = Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { [weak self] _ in
            self?.refresh()
        }
        refreshTimer?.tolerance = 5
    }

    private func setupMenu() {
        let menu = NSMenu()

        let header = NSMenuItem(title: "📊 Usage Monitor for Claude v\(appVersion)",
                                action: nil, keyEquivalent: "")
        menu.addItem(header)
        menu.addItem(.separator())
        menu.addItem(fiveHourItem)
        menu.addItem(allModelsItem)
        menu.addItem(sonnetItem)
        menu.addItem(.separator())
        menu.addItem(todayItem)
        menu.addItem(inputItem)
        menu.addItem(outputItem)
        menu.addItem(costItem)
        menu.addItem(.separator())
        menu.addItem(grantAccessItem)
        menu.addItem(withTitle: "🔄 Refresh", action: #selector(refreshClicked), keyEquivalent: "r")
        menu.addItem(withTitle: "⚙️  Settings…", action: #selector(openSettings), keyEquivalent: ",")
        menu.addItem(autostartItem)
        menu.addItem(.separator())
        menu.addItem(withTitle: "❌ Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")

        for item in menu.items where item.action != #selector(NSApplication.terminate(_:)) {
            item.target = self
        }
        statusItem.menu = menu
    }

    /// Standard Edit menu so Cmd+C/V/X/A work inside dialogs.
    private func setupEditMenu() {
        let mainMenu = NSMenu()
        let editMenu = NSMenu(title: "Edit")
        editMenu.addItem(withTitle: "Undo", action: Selector(("undo:")), keyEquivalent: "z")
        editMenu.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenu.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")

        let editItem = NSMenuItem()
        editItem.submenu = editMenu
        mainMenu.addItem(editItem)
        NSApp.mainMenu = mainMenu
    }

    // MARK: - Refresh

    @objc private func refreshClicked() {
        refresh()
    }

    private func refresh() {
        updateTokenStats()

        let config = ConfigStore.shared
        guard !config.cookie.isEmpty, !config.orgId.isEmpty else {
            statusItem.button?.title = "⚠️"
            fiveHourItem.title = "⏱️  5-Hour: Not configured"
            allModelsItem.title = "🛠️  All Models: Not configured"
            sonnetItem.title = "🔷 Sonnet only: Not configured"
            return
        }

        UsageAPI.fetch(orgId: config.orgId, cookie: config.cookie) { [weak self] result in
            guard let self else { return }
            switch result {
            case .success(let data):
                self.updateUI(data)
            case .failure(.unauthorized):
                self.statusItem.button?.title = "🔒"
                Notifier.notify(title: "Authentication Failed",
                                body: "Session expired, please configure again in Settings.")
            case .failure(.http(let code)):
                self.statusItem.button?.title = "❌"
                self.fiveHourItem.title = "⏱️  Error: HTTP \(code)"
            case .failure(.network(let error)):
                self.statusItem.button?.title = "❌"
                self.fiveHourItem.title = "⏱️  Error: \(error.localizedDescription)"
            case .failure(.invalidResponse):
                self.statusItem.button?.title = "❌"
                self.fiveHourItem.title = "⏱️  Error: invalid response"
            }
        }
    }

    private func updateUI(_ data: UsageResponse) {
        if let fiveHour = data.fiveHour {
            let utilization = fiveHour.utilization ?? 0
            let remaining = Format.timeRemaining(fiveHour.resetsAt)
            let short = Format.timeShort(fiveHour.resetsAt)
            statusItem.button?.title = "\(Int(utilization))% \(short)"
            fiveHourItem.title = "⏱️  5-Hour: \(Format.statusEmoji(utilization: utilization)) "
                + "\(Int(utilization))% (Resets: \(remaining))"

            if utilization >= 95, shouldNotify("usage_critical") {
                Notifier.notify(title: "⚠️ Claude Usage Critical Warning",
                                subtitle: "5-hour limit nearly exhausted",
                                body: "Current usage: \(Int(utilization))%, please reduce usage immediately!")
            } else if utilization >= 90, shouldNotify("usage_high") {
                Notifier.notify(title: "Claude Usage Warning",
                                subtitle: "5-hour limit approaching",
                                body: "Current usage: \(Int(utilization))%, please monitor your usage.")
            }
        } else {
            fiveHourItem.title = "⏱️  5-Hour: No data"
        }

        if let sevenDay = data.sevenDay {
            let utilization = sevenDay.utilization ?? 0
            let remaining = Format.timeRemaining(sevenDay.resetsAt)
            allModelsItem.title = "🛠️  All Models: \(Format.statusEmoji(utilization: utilization)) "
                + "\(Int(utilization))% (Resets: \(remaining))"
        } else {
            allModelsItem.title = "🛠️  All Models: No data"
        }

        if let sonnet = data.sevenDaySonnet {
            let utilization = sonnet.utilization ?? 0
            if utilization == 0 {
                sonnetItem.title = "🔷 Sonnet only: 🟢 0% (Unused)"
            } else {
                let remaining = Format.timeRemaining(sonnet.resetsAt)
                sonnetItem.title = "🔷 Sonnet only: \(Format.statusEmoji(utilization: utilization)) "
                    + "\(Int(utilization))% (Resets: \(remaining))"
            }
        } else {
            sonnetItem.title = "🔷 Sonnet only: No data"
        }
    }

    private func shouldNotify(_ key: String, threshold: TimeInterval = 900) -> Bool {
        let now = Date().timeIntervalSince1970
        if now - (lastNotificationTime[key] ?? 0) > threshold {
            lastNotificationTime[key] = now
            return true
        }
        return false
    }

    // MARK: - Local token stats

    private func updateTokenStats() {
        guard let root = resolveClaudeFolder() else {
            grantAccessItem.isHidden = false
            todayItem.title = "📈 Today: grant folder access to enable"
            inputItem.title = "    ⬇️  Input: –"
            outputItem.title = "    ⬆️  Output: –"
            costItem.title = "💰 Cost: –"
            return
        }
        grantAccessItem.isHidden = true

        DispatchQueue.global(qos: .utility).async { [weak self] in
            let accessing = root.startAccessingSecurityScopedResource()
            let stats = TokenStats.todayStats(claudeRoot: root)
            if accessing { root.stopAccessingSecurityScopedResource() }

            DispatchQueue.main.async {
                self?.renderTokenStats(stats)
            }
        }
    }

    private func renderTokenStats(_ modelUsage: [String: UsageCounts]) {
        guard !modelUsage.isEmpty else {
            todayItem.title = "📈 Today: 0 tokens"
            inputItem.title = "    ⬇️  Input: 0"
            outputItem.title = "    ⬆️  Output: 0"
            costItem.title = "💰 Cost: $0.000"
            return
        }

        let totalInput = modelUsage.values.reduce(0) { $0 + $1.input }
        let totalOutput = modelUsage.values.reduce(0) { $0 + $1.output }

        var totalCost = 0.0
        var costParts: [String] = []
        let sorted = modelUsage.sorted { $0.value.total > $1.value.total }
        for (model, usage) in sorted {
            let cost = TokenStats.matchPricing(for: model).cost(for: usage)
            totalCost += cost

            let shortName = model.contains("/") ? String(model.split(separator: "/").last!) : model
            let icon: String
            if model.lowercased().contains("opus") {
                icon = "💎"
            } else if model.lowercased().contains("haiku") {
                icon = "⚡"
            } else {
                icon = "🔷"
            }
            costParts.append("\(icon) \(shortName) \(Format.cost(cost))")
        }

        todayItem.title = "📈 Today: \(Format.tokens(totalInput + totalOutput)) tokens"
        inputItem.title = "    ⬇️  Input: \(Format.tokens(totalInput))"
        outputItem.title = "    ⬆️  Output: \(Format.tokens(totalOutput))"
        costItem.title = "💰 Cost: \(Format.cost(totalCost))  (\(costParts.prefix(3).joined(separator: "  ")))"
    }

    // MARK: - Folder access (sandbox)

    private func resolveClaudeFolder() -> URL? {
        guard let bookmark = ConfigStore.shared.claudeFolderBookmark else { return nil }
        var stale = false
        guard let url = try? URL(resolvingBookmarkData: bookmark,
                                 options: .withSecurityScope,
                                 relativeTo: nil,
                                 bookmarkDataIsStale: &stale) else { return nil }
        if stale {
            if let fresh = try? url.bookmarkData(options: .withSecurityScope) {
                ConfigStore.shared.claudeFolderBookmark = fresh
            }
        }
        return url
    }

    private func realHomeDirectory() -> URL {
        if let pw = getpwuid(getuid()), let dir = pw.pointee.pw_dir {
            return URL(fileURLWithPath: String(cString: dir), isDirectory: true)
        }
        return FileManager.default.homeDirectoryForCurrentUser
    }

    @objc private func grantFolderAccess() {
        NSApp.activate(ignoringOtherApps: true)

        let panel = NSOpenPanel()
        panel.message = "Select your \"~/.claude\" folder so the app can read Claude Code usage logs (read-only)."
        panel.prompt = "Grant Access"
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = false
        panel.showsHiddenFiles = true
        panel.directoryURL = realHomeDirectory().appendingPathComponent(".claude", isDirectory: true)

        guard panel.runModal() == .OK, let url = panel.url else { return }

        do {
            ConfigStore.shared.claudeFolderBookmark = try url.bookmarkData(options: .withSecurityScope)
            refresh()
        } catch {
            showAlert(title: "Error", message: "Could not save folder access: \(error.localizedDescription)")
        }
    }

    // MARK: - Settings / onboarding

    private func showWelcomeGuide() {
        let response = showAlert(
            title: "Welcome to Usage Monitor for Claude",
            message: """
            Thank you for using Usage Monitor for Claude!

            Setup only takes one step:
            Copy a cURL command from your browser's DevTools
            and paste it here. That's it!

            Click "Configure Now" to get started.
            """,
            ok: "Configure Now", cancel: "Later")
        if response {
            runSettingsFlow()
        }
    }

    @objc private func openSettings() {
        runSettingsFlow()
    }

    private func runSettingsFlow() {
        let openPage = showAlert(
            title: "Configure Usage Monitor",
            message: """
            Click "Open Usage Page" to open claude.ai, then:

            1. Press F12 (or Cmd+Option+I) → Network tab
            2. Refresh the page
            3. Find any request (e.g. "usage")
            4. Right-click → Copy as cURL

            After copying, come back and continue.
            """,
            ok: "Open Usage Page", cancel: "Read from Clipboard")

        if openPage {
            NSWorkspace.shared.open(URL(string: "https://claude.ai/settings/usage")!)
            _ = showAlert(
                title: "Next Step",
                message: "After copying the cURL command (Cmd+C),\nclick the button below to configure.",
                ok: "Read from Clipboard")
        }

        guard let clipboard = NSPasteboard.general.string(forType: .string),
              !clipboard.isEmpty else {
            _ = showAlert(title: "Error",
                          message: "Clipboard is empty.\nPlease copy the cURL command first.")
            return
        }

        let (cookie, orgId) = CurlParser.parse(clipboard)

        guard let cookie else {
            _ = showAlert(title: "Parse Failed", message: """
                Could not find sessionKey in clipboard content.

                Make sure you right-clicked a request on claude.ai
                and selected "Copy as cURL".
                """)
            return
        }
        guard let orgId else {
            _ = showAlert(title: "Parse Failed", message: """
                Could not find Organization ID.

                Make sure you copied a cURL from claude.ai.
                """)
            return
        }

        ConfigStore.shared.cookie = cookie
        ConfigStore.shared.orgId = orgId
        refresh()
        Notifier.notify(title: "Configuration Saved",
                        body: "Credentials stored in Keychain, refreshing...")
    }

    // MARK: - Launch at login

    private func updateAutostartMenu() {
        autostartItem.title = Autostart.isEnabled ? "🚀 Launch at Login ✓" : "🚀 Launch at Login"
    }

    @objc private func toggleAutostart() {
        do {
            let enabled = try Autostart.toggle()
            updateAutostartMenu()
            Notifier.notify(title: enabled ? "Launch at Login Enabled" : "Launch at Login Disabled",
                            body: enabled ? "Will launch automatically when you log in."
                                          : "Removed from login items.")
        } catch {
            showAlert(title: "Error", message: "Failed to update login item: \(error.localizedDescription)")
        }
    }

    // MARK: - Alert helper

    @discardableResult
    private func showAlert(title: String, message: String,
                           ok: String = "OK", cancel: String? = nil) -> Bool {
        NSApp.activate(ignoringOtherApps: true)
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = message
        alert.addButton(withTitle: ok)
        if let cancel {
            alert.addButton(withTitle: cancel)
        }
        alert.window.level = .floating
        return alert.runModal() == .alertFirstButtonReturn
    }
}
