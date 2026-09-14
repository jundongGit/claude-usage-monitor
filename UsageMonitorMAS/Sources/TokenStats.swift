import Foundation

struct UsageCounts {
    var input = 0
    var output = 0
    var cacheRead = 0
    var cacheCreate = 0

    var total: Int { input + output + cacheRead + cacheCreate }

    mutating func add(_ other: UsageCounts) {
        input += other.input
        output += other.output
        cacheRead += other.cacheRead
        cacheCreate += other.cacheCreate
    }
}

struct ModelPricing {
    let input: Double
    let output: Double
    let cacheRead: Double
    let cacheCreate: Double

    func cost(for usage: UsageCounts) -> Double {
        Double(usage.input) / 1e6 * input
            + Double(usage.output) / 1e6 * output
            + Double(usage.cacheRead) / 1e6 * cacheRead
            + Double(usage.cacheCreate) / 1e6 * cacheCreate
    }
}

/// Reads Claude Code's local JSONL transcripts (inside the user-granted
/// folder) and aggregates today's token usage per model.
enum TokenStats {

    static let pricing: [String: ModelPricing] = [
        "opus": ModelPricing(input: 15, output: 75, cacheRead: 1.5, cacheCreate: 18.75),
        "sonnet": ModelPricing(input: 3, output: 15, cacheRead: 0.3, cacheCreate: 3.75),
        "haiku": ModelPricing(input: 0.8, output: 4, cacheRead: 0.08, cacheCreate: 1.0),
    ]

    static func matchPricing(for model: String) -> ModelPricing {
        let lower = model.lowercased()
        for key in ["opus", "haiku", "sonnet"] where lower.contains(key) {
            return pricing[key]!
        }
        return pricing["sonnet"]!
    }

    /// `claudeRoot` is the user-selected `~/.claude` folder (security-scoped).
    static func todayStats(claudeRoot: URL) -> [String: UsageCounts] {
        let projectsDir = claudeRoot.appendingPathComponent("projects", isDirectory: true)
        let fm = FileManager.default
        guard let projectDirs = try? fm.contentsOfDirectory(
            at: projectsDir, includingPropertiesForKeys: [.isDirectoryKey]
        ) else { return [:] }

        let calendar = Calendar.current
        let startOfToday = calendar.startOfDay(for: Date())

        // Streaming dedup: keep the record with max output tokens per message id.
        var bestById: [String: (output: Int, model: String, usage: UsageCounts)] = [:]
        var anonymous: [(model: String, usage: UsageCounts)] = []

        for projDir in projectDirs {
            guard (try? projDir.resourceValues(forKeys: [.isDirectoryKey]))?.isDirectory == true,
                  let files = try? fm.contentsOfDirectory(
                    at: projDir, includingPropertiesForKeys: [.contentModificationDateKey]
                  ) else { continue }

            for file in files {
                guard file.pathExtension == "jsonl",
                      !file.lastPathComponent.hasPrefix("agent-") else { continue }
                // Skip files not modified today (optimization, mirrors the original app)
                if let mtime = (try? file.resourceValues(forKeys: [.contentModificationDateKey]))?.contentModificationDate,
                   mtime < startOfToday { continue }

                guard let content = try? String(contentsOf: file, encoding: .utf8) else { continue }

                for line in content.split(separator: "\n") {
                    guard let obj = try? JSONSerialization.jsonObject(
                        with: Data(line.utf8)) as? [String: Any],
                        obj["type"] as? String == "assistant",
                        let message = obj["message"] as? [String: Any],
                        let rawUsage = message["usage"] as? [String: Any],
                        !rawUsage.isEmpty
                    else { continue }

                    guard let ts = obj["timestamp"], let date = parseTimestamp(ts),
                          calendar.isDateInToday(date) else { continue }

                    let usage = UsageCounts(
                        input: intValue(rawUsage["input_tokens"]),
                        output: intValue(rawUsage["output_tokens"]),
                        cacheRead: intValue(rawUsage["cache_read_input_tokens"]),
                        cacheCreate: intValue(rawUsage["cache_creation_input_tokens"])
                    )

                    var model = (message["model"] as? String) ?? "unknown"
                    if model.hasPrefix("<") { model = "unknown" }

                    if let msgId = message["id"] as? String, !msgId.isEmpty {
                        if let existing = bestById[msgId], usage.output <= existing.output { continue }
                        bestById[msgId] = (usage.output, model, usage)
                    } else {
                        anonymous.append((model, usage))
                    }
                }
            }
        }

        var result: [String: UsageCounts] = [:]
        for record in bestById.values {
            result[record.model, default: UsageCounts()].add(record.usage)
        }
        for record in anonymous {
            result[record.model, default: UsageCounts()].add(record.usage)
        }
        return result
    }

    private static func intValue(_ any: Any?) -> Int {
        if let n = any as? Int { return n }
        if let n = any as? Double { return Int(n) }
        return 0
    }

    private static let isoFractional: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    private static let isoPlain = ISO8601DateFormatter()

    private static func parseTimestamp(_ ts: Any) -> Date? {
        if let ms = ts as? Double {
            return Date(timeIntervalSince1970: ms / 1000)
        }
        if let str = ts as? String {
            if let allDigits = Double(str), str.allSatisfy(\.isNumber) {
                return Date(timeIntervalSince1970: allDigits / 1000)
            }
            return isoFractional.date(from: str) ?? isoPlain.date(from: str)
        }
        return nil
    }
}
