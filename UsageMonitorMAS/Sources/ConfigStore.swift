import Foundation
import Security

/// Persists configuration. The session cookie (a credential) lives in the
/// Keychain; non-sensitive values live in UserDefaults.
final class ConfigStore {
    static let shared = ConfigStore()

    private let keychainService = "nz.co.worldway.usagemonitor"
    private let cookieAccount = "claude-session-cookie"
    private let defaults = UserDefaults.standard

    private enum Key {
        static let orgId = "orgId"
        static let claudeFolderBookmark = "claudeFolderBookmark"
    }

    var orgId: String {
        get { defaults.string(forKey: Key.orgId) ?? "" }
        set { defaults.set(newValue, forKey: Key.orgId) }
    }

    var claudeFolderBookmark: Data? {
        get { defaults.data(forKey: Key.claudeFolderBookmark) }
        set { defaults.set(newValue, forKey: Key.claudeFolderBookmark) }
    }

    // MARK: - Cookie (Keychain)

    var cookie: String {
        get { readKeychain() ?? "" }
        set {
            if newValue.isEmpty {
                deleteKeychain()
            } else {
                writeKeychain(newValue)
            }
        }
    }

    private func baseQuery() -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: cookieAccount,
        ]
    }

    private func readKeychain() -> String? {
        var query = baseQuery()
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess, let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    private func writeKeychain(_ value: String) {
        let data = Data(value.utf8)
        let query = baseQuery()
        let attributes: [String: Any] = [kSecValueData as String: data]

        let status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            var addQuery = query
            addQuery[kSecValueData as String] = data
            addQuery[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
            SecItemAdd(addQuery as CFDictionary, nil)
        }
    }

    private func deleteKeychain() {
        SecItemDelete(baseQuery() as CFDictionary)
    }
}
