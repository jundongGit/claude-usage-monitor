import Foundation

/// Parses a cURL command copied from browser DevTools to extract the
/// Claude session cookie and organization ID.
enum CurlParser {

    private static let uuidPattern = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    static func parse(_ text: String) -> (cookie: String?, orgId: String?) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return (nil, nil) }

        var orgId = firstMatch(in: trimmed, pattern: "/organizations/(\(uuidPattern))")

        // Cookie may come via -H 'Cookie: ...' / -b '...' with either quote style.
        // Quote types must match because cookie values can contain " from JSON.
        let cookiePatterns = [
            "(?:-H|--header)\\s+'[Cc]ookie:\\s*([^']*)'",
            "(?:-H|--header)\\s+\"[Cc]ookie:\\s*([^\"]*)\"",
            "(?:-b|--cookie)\\s+'([^']*)'",
            "(?:-b|--cookie)\\s+\"([^\"]*)\"",
        ]

        var cookie: String?
        for pattern in cookiePatterns {
            guard let cookieStr = firstMatch(in: trimmed, pattern: pattern, options: [.dotMatchesLineSeparators]) else { continue }
            let cleaned = cookieStr.trimmingCharacters(in: .whitespacesAndNewlines)
            if cleaned.contains("sessionKey=") {
                cookie = cleaned
            }
            if orgId == nil {
                orgId = firstMatch(in: cleaned, pattern: "lastActiveOrg=(\(uuidPattern))")
            }
            break
        }

        return (cookie, orgId)
    }

    private static func firstMatch(in text: String, pattern: String,
                                   options: NSRegularExpression.Options = []) -> String? {
        guard let regex = try? NSRegularExpression(pattern: pattern, options: options) else { return nil }
        let range = NSRange(text.startIndex..., in: text)
        guard let match = regex.firstMatch(in: text, range: range),
              match.numberOfRanges > 1,
              let groupRange = Range(match.range(at: 1), in: text) else { return nil }
        return String(text[groupRange])
    }
}
