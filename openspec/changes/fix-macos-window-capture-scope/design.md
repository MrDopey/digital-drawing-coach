## Context

`CaptureEngine._do_capture` (`src/drawing_coach/capture_engine.py`) fetches the target window's bounds via `WindowManager.get_window_rect()` and always captures through `mss.mss().grab({"left", "top", "width", "height"})`, on every platform.

On macOS, `mss`'s implementation (`mss/darwin.py`) captures with:
```python
core.CGWindowListCreateImage(rect, 1, 0, IMAGE_OPTIONS)
```
`rect` is the screen rectangle to render, `1` is `kCGWindowListOptionOnScreenOnly`, and `0` is `kCGNullWindowID`. This is CoreGraphics' region-compositing API: it renders *whatever is on-screen* inside `rect`, from all windows, not the content of one specific window. It is the correct call for "grab this rectangle of the display" (which is all `mss` needs for its monitor-capture use case), but it is the wrong call for "grab this one window," because:
- Any window on top of the target window at that screen location bleeds into the capture.
- If the target window's last-known bounds are stale (e.g., it moved, resized, or the ID briefly resolves to a different/larger window), the capture silently reflects whatever is actually on screen there instead of failing loudly.
- The captured frame is never verified against the window's actual, current content — a rect that happens to match (or exceed) full-screen dimensions produces a full-screen capture with no distinguishing signal.

CoreGraphics separately supports capturing a specific window's content directly, regardless of what's on top of it:
```c
CGWindowListCreateImage(CGRectNull, kCGWindowListOptionIncludingWindow, windowID, imageOption)
```
Passing `CGRectNull` tells CoreGraphics to use the window's own bounds and content rather than a caller-supplied screen rectangle, and `kCGWindowListOptionIncludingWindow` + a real `windowID` scopes the render strictly to that window. This is Apple's documented single-window screenshot pattern and sidesteps the region/overlap ambiguity entirely.

## Goals / Non-Goals

**Goals:**
- On macOS, a captured frame contains only the selected window's own rendered content.
- No behavior change on Windows/Linux (they don't share this bug — `mss` isn't macOS's problem there).
- Keep `CaptureEngine` platform-agnostic; platform-specific capture mechanics stay inside the `WindowBackend` implementations.

**Non-Goals:**
- Not fixing window *selection*/enumeration (`list_windows`) — this change is only about what gets rendered once a window is selected.
- Not changing dedup, storage, or session format.
- Not adding a generic "region capture" capability; the fix is specifically about window-scoped capture.

## Decisions

**Decision: Add a `capture_image(window_id) -> Image.Image | None` method to `WindowBackend`, implemented per platform, and have `CaptureEngine` call it instead of calling `mss` directly.**
- Windows/Linux backends implement it by keeping the existing `mss.grab()` + rect approach (via `get_window_rect`), preserving current behavior exactly.
- The macOS backend implements it via direct `Quartz`/CoreGraphics `CGWindowListCreateImage(CGRectNull, kCGWindowListOptionIncludingWindow, windowID, imageOption)`, converting the returned `CGImage` to a PIL `Image` the same way `mss.darwin` does (read bytes via `CGDataProvider`, strip row padding, wrap with `Image.frombytes`).
- Alternative considered: keep using `mss.grab()` on macOS but clamp/crop the result more aggressively, or cross-check returned size against expected bounds. Rejected — this only reduces the blast radius of the bug (e.g., catches "returned image is much bigger than expected") but does nothing about occlusion by overlapping windows, which is the more common real-world trigger (a floating panel, notification, or another visible app window over part of the drawing app).
- Alternative considered: switch the whole app (all platforms) to a different capture library. Rejected — Windows/Linux capture already works correctly; only macOS's approach is unsound for window-scoped capture.

**Decision: `get_window_rect` stays as-is and is still used for zero-size / window-lost detection (`_do_capture`'s existing `rect is None` / `width <= 0` checks), just not for building the mss grab dict on macOS.**
- Keeps the "window lost" and "minimized" detection paths unchanged, since those depend on bounds, not pixel content.

## Risks / Trade-offs

- [`CGWindowListCreateImage` with `kCGWindowListOptionIncludingWindow` can return `None`/empty if the window is fully occluded by a modal system UI element, or minimized] → Treat a `None`/empty result the same as "window lost" (existing `on_window_lost` path), same as today's `rect is None` handling.
- [Behavior can only be verified on real macOS hardware; this environment has no macOS to run it on] → Cover the new macOS backend method with unit tests that mock `Quartz`/ctypes calls (matching the existing test style for `has_screen_recording_permission` etc.), and note in tasks.md that manual verification on a Mac is required before closing out the change.
- [Minor: capturing "the window's own bounds" via `CGRectNull` means the resulting image size may differ slightly from what `get_window_rect` reports (window shadows/borders excluded) — same as current behavior, not a regression] → No action needed, existing dedup (`_compute_mae`) already resizes for comparison.

## Migration Plan

No data migration. This is a behavior-only fix scoped to the macOS capture path:
1. Add `capture_image` to the `WindowBackend` protocol and all three backend implementations.
2. Switch `CaptureEngine._do_capture` to call `manager.capture_image(...)` instead of instantiating `mss.mss()` directly.
3. Ship as a normal patch release; no feature flag needed since the old behavior was strictly a bug.
4. Rollback: revert the commit — the old mss-based path is unchanged on Windows/Linux and fully removed only from the macOS backend, not deleted from `capture_engine.py`'s dependencies (mss remains a dependency for the other two platforms).

## Open Questions

- None blocking — the CoreGraphics single-window capture pattern is well-established. Final confirmation should come from manual testing on macOS with an overlapping window scenario (see tasks.md).
