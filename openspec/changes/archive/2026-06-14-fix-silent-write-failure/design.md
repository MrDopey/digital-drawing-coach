## Context

`CaptureEngine._write_frame` wraps `img.save()` in a bare `except Exception: return None`. Callers treat `None` as "no session directory" (legitimate in-memory mode), so a disk error produces an indistinguishable silent failure. `MainWindow` has no mechanism to learn that writes are failing and no status bar to display that information.

The current `_status_label` in the center of the window shows capture state (stopped / paused / active). It is not the right place for a persistent error indicator. A `QStatusBar` pinned to the bottom of the window is the standard Qt pattern.

## Goals / Non-Goals

**Goals:**
- Surface write failures to the user in a visible, non-blocking UI element.
- Show a one-line summary in the status bar; full error + permission fix instructions on hover.
- Allow the user to highlight and copy the full error text.
- Clear the warning automatically when the next frame saves successfully.
- Log a WARNING each time a write fails (developer observability).

**Non-Goals:**
- Retry logic for transient write errors.
- Blocking the user or requiring action to dismiss.
- Detecting or fixing permissions automatically.

## Decisions

**1. `on_write_error: Callable[[Path, Exception], None] | None` callback on `CaptureEngine`**

`_write_frame` already calls `on_frame_captured` on success. Adding a parallel `on_write_error` callback keeps the engine decoupled from the UI and follows the existing event pattern. The callback receives the target `Path` and the raised `Exception` so callers get enough detail to build a helpful message.

A dedicated error signal was considered but Qt signals require `QObject` inheritance — adding that to `CaptureEngine` is heavier than a plain callable. The existing `on_frame_captured` is also a callable, so this is consistent.

**2. `QStatusBar` via `self.statusBar()` with a permanent `QLabel`**

`QMainWindow.statusBar()` lazily creates a `QStatusBar` and positions it at the bottom of the window below the central widget — exactly where it belongs. A permanent widget added with `statusBar().addPermanentWidget(label)` is always visible and does not get replaced by transient `showMessage()` calls.

The label uses `setTextInteractionFlags(TextSelectableByMouse | TextSelectableByKeyboard)` so the one-liner is highlightable and copyable directly in the status bar.

**3. Copyable hover popup for full error**

`QToolTip` text cannot be highlighted or copied. A lightweight custom `QFrame` (borderless, `StaysOnTopHint`, `ToolTip` window flag) containing a read-only `QPlainTextEdit` with `TextSelectableByMouse` is shown on `enterEvent` of the status label and hidden on `leaveEvent`. The popup is positioned just above the status bar. This matches the UX the user described: hover to see full detail, text is selectable.

**4. Clear on recovery**

`_store_frame` already returns `None` on write failure and a `CapturedFrame` on success. When `on_frame_captured` fires (success path), `MainWindow` clears the status bar warning. This requires no extra callback — reuse `on_frame_captured` as the "recovery" signal.

**5. Permission-fix instructions in the popup**

The popup body is built at runtime from the values passed to `on_write_error(path, exc)`:

```
Frame write failed: <path>
Error: <str(exc)>

To fix:
• Ensure this directory is writable:
    <path.parent>
• Check available disk space.
• On macOS, check System Settings → Privacy & Security → Files and Folders.
```

`path` and `path.parent` are the actual values received in the callback — no hardcoded directory strings. No OS detection is needed in the first cut.

## Risks / Trade-offs

- [Noise on repeated failures] Every failed frame calls `on_write_error`, which updates the label. The label text is stable (same message), so there is no visible flicker. Log noise is expected and intentional.
- [Popup dismissed unexpectedly] If the user moves the mouse off the label while reading, the popup closes. Mitigation: the one-liner in the status bar is always visible and selectable, so they can still copy the path without the popup.
