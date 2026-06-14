## 1. Fix and split backend permission checks

- [x] 1.1 In `src/drawing_coach/_backend_macos.py`, rename the current `has_input_monitoring_permission` body into a new `has_accessibility_permission` function (keeping `AXIsProcessTrustedWithOptions` — that is the correct API for Accessibility).
- [x] 1.2 In `src/drawing_coach/_backend_macos.py`, rewrite `has_input_monitoring_permission` to load `IOKit` via `ctypes.util.find_library("IOKit")`, call `IOHIDCheckAccess(1)` (`kIOHIDRequestTypeListenEvent = 1`), and return `True` only when the result is `0` (`kIOHIDAccessTypeGranted`). Wrap in try/except and return `False` on any error.

## 2. Add and fix diagnostic check functions

- [x] 2.1 In `src/drawing_coach/diagnostics.py`, add a `check_accessibility()` function that imports `has_accessibility_permission` and returns a `CheckResult` named "Accessibility" with the hint "Open System Settings → Privacy & Security → Accessibility and enable Drawing Coach" on failure.
- [x] 2.2 In `src/drawing_coach/diagnostics.py`, update `check_input_monitoring()` to import the fixed `has_input_monitoring_permission` (no logic change needed — the hint text is already correct).
- [x] 2.3 In `src/drawing_coach/diagnostics.py`, register `check_accessibility` in the macOS checks list immediately before `check_input_monitoring` so both rows appear together in the dialog.

## 3. Update spec

- [x] 3.1 In `openspec/specs/system-diagnostics/spec.md`, apply the delta from `openspec/changes/fix-input-monitoring-permission-check/specs/system-diagnostics/spec.md`: add the Accessibility requirement and update the Input Monitoring requirement to reference `IOHIDCheckAccess`.

## 4. Documentation

- [x] 4.1 Review `README.md` for any developer notes about macOS permissions and update if needed.
- [x] 4.2 Review `.claude/CLAUDE.md` — no new conventions introduced; confirm no update is needed.
- [x] 4.3 Review `openspec/config.yaml` — no recurring spec gap revealed; confirm no change is needed.

## 5. Verification

- [x] 5.1 Run `uv run pytest` and confirm all tests pass.
