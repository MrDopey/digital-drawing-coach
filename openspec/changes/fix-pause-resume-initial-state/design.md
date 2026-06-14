## Context

`CaptureEngine.start()` is called unconditionally in `MainWindow.__init__` but the capture loop skips every tick when `self._target is None` (line 215). The button is constructed with `QPushButton("Pause")` at line 251 and `_toggle_pause` only checks `self._capture.paused` — it has no awareness of the no-target state. The system tray action mirrors the same text.

## Goals / Non-Goals

**Goals:**
- Button reads "Start Capture" when no window is selected
- Button transitions to "Pause" once a window is selected and capturing begins
- "Start Capture" click opens the window picker (same as clicking the "Select Window" button)
- Tray action keeps in sync

**Non-Goals:**
- Changing when `CaptureEngine.start()` is called (lazy start is a larger refactor)
- Adding a separate "Stop" state

## Decisions

### 1. Three UI states keyed on `(target is None, paused)`

| State | `target` | `paused` | Button label | Tray label |
|---|---|---|---|---|
| Not started | `None` | any | `Start Capture` | `Select Window` |
| Running | set | `False` | `Pause` | `Pause Capture` |
| Paused | set | `True` | `Resume` | `Resume Capture` |

`_update_capture_btn()` (new helper) computes the label from these two conditions and is called from `_update_status` and after `_toggle_pause`.

### 2. Clicking "Start Capture" opens the window picker

`_toggle_pause` checks `self._capture.target is None` first; if true, it calls `_select_window()` instead of pause/resume. This reuses existing logic with no new code paths.

**Alternative:** Disable the button until a window is selected — rejected because a disabled button gives no affordance; clicking it and getting the window picker is more discoverable.

## Risks / Trade-offs

- [User selects window, then pauses before first capture — button shows "Pause" immediately] → correct; the button reflects intent (capture is configured and will run), not the first screenshot having arrived
