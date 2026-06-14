## Why

`CaptureEngine._write_frame` swallows all exceptions from `img.save()` without logging anything and without notifying the UI. When writes fail (disk full, permission denied), the user continues drawing while every frame is silently discarded — all session history will be lost when the application closes. There is no indication anywhere that anything is wrong.

## What Changes

- **Backend:** Add an `on_write_error` callback to `CaptureEngine`; call it (and log a WARNING) when `img.save()` raises an exception.
- **UI:** Add a `QStatusBar` to the main window. When a write failure is reported, the status bar shows a one-line warning: "⚠ Frame saves failing — images will be lost if the app closes." Hovering over the warning opens a copyable popup showing the full error and instructions for fixing file-system permissions.
- **Clear on recovery:** The warning is cleared the next time a frame is saved successfully.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `screenshot-capture`: Add requirements for (1) the `on_write_error` callback on `CaptureEngine`, (2) the status bar warning shown in the main window, and (3) the copyable hover popup with full error detail and permission-fix guidance.

## Impact

- `src/drawing_coach/capture_engine.py` — `_write_frame` calls `on_write_error`; logging added
- `src/drawing_coach/main_window.py` — `QStatusBar` added; `on_write_error` wired to update it; custom hover popup widget
