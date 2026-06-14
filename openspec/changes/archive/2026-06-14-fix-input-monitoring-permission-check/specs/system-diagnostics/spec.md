## ADDED Requirements

### Requirement: Accessibility permission check (macOS only)
The system SHALL verify on macOS that the app has Accessibility permission (required for window listing and UI automation), reporting a clear pass or fail with a targeted remediation hint when it fails. On non-macOS platforms this check SHALL be skipped (not shown as a row). The check SHALL use `AXIsProcessTrustedWithOptions(NULL)` from ApplicationServices.

#### Scenario: macOS — Accessibility permission granted
- **WHEN** the diagnostics run on macOS and `AXIsProcessTrustedWithOptions(NULL)` returns `True`
- **THEN** the Accessibility check shows ✓ and the message "Accessibility permission granted"

#### Scenario: macOS — Accessibility permission denied
- **WHEN** the diagnostics run on macOS and `AXIsProcessTrustedWithOptions(NULL)` returns `False`
- **THEN** the Accessibility check shows ✗, the message "Accessibility permission denied", and the hint "Open System Settings → Privacy & Security → Accessibility and enable Drawing Coach"

## MODIFIED Requirements

### Requirement: Input Monitoring permission check (macOS only)
The system SHALL verify on macOS that the app has Input Monitoring permission so that global hotkeys function, reporting a clear pass or fail with a remediation hint when it fails. On non-macOS platforms this check SHALL be skipped (not shown as a row). The check SHALL use `IOHIDCheckAccess(kIOHIDRequestTypeListenEvent)` from IOKit, which directly interrogates the Input Monitoring TCC category.

#### Scenario: macOS — Input Monitoring permission granted
- **WHEN** the diagnostics run on macOS and `IOHIDCheckAccess(kIOHIDRequestTypeListenEvent)` returns `kIOHIDAccessTypeGranted` (0)
- **THEN** the Input Monitoring check shows ✓ and the message "Input Monitoring permission granted"

#### Scenario: macOS — Input Monitoring permission denied
- **WHEN** the diagnostics run on macOS and `IOHIDCheckAccess(kIOHIDRequestTypeListenEvent)` returns `kIOHIDAccessTypeDenied` (1) or `kIOHIDAccessTypeUnknown` (2)
- **THEN** the Input Monitoring check shows ✗, the message "Input Monitoring permission denied", and the hint "Open System Settings → Privacy & Security → Input Monitoring and enable Drawing Coach; hotkeys will not work without this"
