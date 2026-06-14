## Why

`has_input_monitoring_permission()` calls `AXIsProcessTrustedWithOptions`, which checks the macOS **Accessibility** permission — not Input Monitoring. These are two distinct macOS TCC categories that control different things: Accessibility enables UI automation and window introspection; Input Monitoring grants access to global keyboard/mouse event taps. Because the single diagnostic check conflates them, a user could be granted one permission and denied the other, yet see a misleading pass or fail, and be directed to the wrong settings pane.

Splitting into one check per permission means each failure surfaces a targeted, unambiguous hint.

## What Changes

- Add `has_accessibility_permission()` to `_backend_macos.py` using `AXIsProcessTrustedWithOptions` — the correct API for that category.
- Fix `has_input_monitoring_permission()` to use `IOHIDCheckAccess(kIOHIDRequestTypeListenEvent)` from IOKit, which directly interrogates the Input Monitoring TCC category.
- In `diagnostics.py`, replace the single `check_input_monitoring` with two separate check functions: `check_accessibility` and `check_input_monitoring`. Register both in the macOS check list.
- Update the `system-diagnostics` spec to add the Accessibility check requirement and correct the Input Monitoring check requirement.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `system-diagnostics`: Add an Accessibility permission check requirement (macOS only); update the Input Monitoring check requirement to reference `IOHIDCheckAccess` and remove the reference to `AXIsProcessTrustedWithOptions`.

## Impact

- `src/drawing_coach/_backend_macos.py` — add `has_accessibility_permission`; fix `has_input_monitoring_permission`
- `src/drawing_coach/diagnostics.py` — add `check_accessibility`; fix `check_input_monitoring`; register both in the macOS checks list
- `openspec/specs/system-diagnostics/spec.md` — new Accessibility requirement; updated Input Monitoring requirement
