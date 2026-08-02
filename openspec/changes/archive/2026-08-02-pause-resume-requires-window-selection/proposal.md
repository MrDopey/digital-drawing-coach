## Why

The Pause/Resume button is enabled and shows "Pause" from app launch, before any drawing window has been selected. Clicking it in that state calls `CaptureEngine.pause()` on a capture that has no target and is already effectively idle, which is confusing: the button implies capture is running when nothing is being monitored. The button should reflect reality — capture cannot run without a target window — and should be disabled until a window is selected.

## What Changes

- On startup and whenever no window is targeted (including after the target window is lost/closed), the Pause/Resume button SHALL show "Resume" (the paused-state label) and SHALL be disabled.
- Once a window is selected via "Select Window", the button SHALL become enabled and behave as it does today (toggling pause/resume, label reflects current state).
- If the target window is lost while capture is running, the button SHALL return to the disabled "Resume" state until a new window is selected.
- The tray menu's "Pause Capture" / "Resume Capture" action SHALL mirror the same enabled/disabled behavior as the main window button.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `screenshot-capture`: The "Capture can be paused and resumed" requirement is extended so the pause/resume control is disabled (and shows the paused label) whenever no drawing window is targeted, and only becomes usable after a window is selected.

## Impact

- `src/drawing_coach/main_window.py`: `_update_status()` (button/tray enabled state), `_build_ui()` (initial disabled state before any target is set), `_open_app_selection()` (enable on successful selection), `_on_window_lost()` (revert to disabled).
- No changes to `CaptureEngine` itself — this is a UI-state fix; `pause()`/`resume()` semantics are unchanged.
