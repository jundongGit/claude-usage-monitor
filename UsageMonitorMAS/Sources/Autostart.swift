import Foundation
import ServiceManagement

/// Launch-at-login via SMAppService — the only App Store–compliant mechanism.
enum Autostart {

    static var isEnabled: Bool {
        SMAppService.mainApp.status == .enabled
    }

    /// Returns the new state after toggling.
    static func toggle() throws -> Bool {
        if isEnabled {
            try SMAppService.mainApp.unregister()
            return false
        } else {
            try SMAppService.mainApp.register()
            return true
        }
    }
}
