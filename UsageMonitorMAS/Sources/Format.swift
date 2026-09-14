import Foundation

enum Format {

    static func tokens(_ n: Int) -> String {
        if n >= 1_000_000 { return String(format: "%.1fM", Double(n) / 1_000_000) }
        if n >= 1_000 { return String(format: "%.1fK", Double(n) / 1_000) }
        return String(n)
    }

    static func cost(_ n: Double) -> String {
        if n >= 100 { return String(format: "$%.0f", n) }
        if n >= 1 { return String(format: "$%.2f", n) }
        return String(format: "$%.3f", n)
    }

    static func statusEmoji(utilization: Double) -> String {
        if utilization >= 90 { return "🔴" }
        if utilization >= 70 { return "🟡" }
        return "🟢"
    }

    private static let isoFractional: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    private static let isoPlain = ISO8601DateFormatter()

    static func parseResetTime(_ str: String?) -> Date? {
        guard let str, !str.isEmpty else { return nil }
        return isoFractional.date(from: str) ?? isoPlain.date(from: str)
    }

    /// "2d 8hr" / "1hr 23min" / "23min" — for menu rows
    static func timeRemaining(_ resetTimeStr: String?) -> String {
        guard let reset = parseResetTime(resetTimeStr) else { return "Unused" }
        let seconds = reset.timeIntervalSinceNow
        if seconds < 0 { return "Expired" }

        let hours = Int(seconds) / 3600
        let minutes = (Int(seconds) % 3600) / 60
        if hours > 24 { return "\(hours / 24)d \(hours % 24)hr" }
        if hours > 0 { return "\(hours)hr \(minutes)min" }
        return "\(minutes)min"
    }

    /// "2d8h" / "1h23m" / "23m" — for the status bar
    static func timeShort(_ resetTimeStr: String?) -> String {
        guard let reset = parseResetTime(resetTimeStr) else { return "" }
        let seconds = reset.timeIntervalSinceNow
        if seconds < 0 { return "Expired" }

        let hours = Int(seconds) / 3600
        let minutes = (Int(seconds) % 3600) / 60
        if hours > 24 { return "\(hours / 24)d\(hours % 24)h" }
        if hours > 0 { return "\(hours)h\(minutes)m" }
        return "\(minutes)m"
    }
}
