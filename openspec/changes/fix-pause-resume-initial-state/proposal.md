## Why

On first launch the main window shows a "Pause" button, implying that capture is running — but no drawing window has been selected yet, so nothing is actually being captured. This misleads new users into thinking they need to pause something that hasn't started, and makes the UI feel broken.

## What Changes

- The button shows **"Start Capture"** on launch (before any drawing window is selected)
- Once a drawing window is selected and capture begins, the button switches to its normal **"Pause" / "Resume"** cycle
- The system tray action follows the same three-state logic

## Capabilities

### New Capabilities

### Modified Capabilities
- `screenshot-capture`: The pause/resume control SHALL display a third "not yet started" state when no target window has been selected; it transitions to the Pause/Resume cycle only after a target is set

## Impact

- `src/drawing_coach/main_window.py` — `_update_status` and `_toggle_pause` updated to handle the pre-target state; `_pause_btn` initial label changed to "Start Capture"
- No changes to `CaptureEngine` — the `target is None` guard already exists; the fix is purely in the UI layer
