## Why

On macOS, captured frames show the entire screen instead of just the drawing app window the user selected. The macOS backend hands `mss` the target window's bounds as if they were a monitor region, but `mss`'s macOS implementation captures a *screen rectangle* (compositing whatever is on-screen there), not a specific window's content — so overlapping windows, stale bounds, or off-screen/occluded windows all bleed into the capture instead of being excluded. This defeats the coaching feature's purpose (the LLM sees the wrong content) and can leak unrelated on-screen content (other apps, notifications, messages) into stored session frames.

## What Changes

- Replace the macOS capture path's use of `mss.grab()` (rect-based, region-compositing) with a direct CoreGraphics call scoped to the target window's ID: `CGWindowListCreateImage(CGRectNull, kCGWindowListOptionIncludingWindow, windowID, imageOption)`. This is Apple's documented pattern for capturing exactly one window's content, regardless of what overlaps it on screen.
- Introduce a per-platform "capture image" seam: `WindowBackend` gains a method to produce the frame image directly (macOS implements it via CoreGraphics; Windows/Linux keep using `mss` with the existing rect-based approach, since that limitation is macOS-specific to how `mss.darwin` is implemented).
- `CaptureEngine._do_capture` calls the backend's capture method instead of always going through `mss` with a raw rect on all platforms.
- Add a regression test asserting the macOS backend captures by window ID, not by screen rect.

## Capabilities

### Modified Capabilities
- `screenshot-capture`: The periodic capture requirement is clarified so a captured frame SHALL contain only the selected window's own content, not other on-screen windows or desktop area, even when other windows overlap or obscure it on screen.

## Impact

- `src/drawing_coach/_backend_macos.py`: replace mss-based grab for macOS with a direct CoreGraphics/Quartz window capture.
- `src/drawing_coach/window_manager.py`: extend the `WindowBackend` protocol with a capture method; other backends (`_backend_windows.py`, `_backend_linux.py`) get a default/mss-based implementation so behavior there is unchanged.
- `src/drawing_coach/capture_engine.py`: `_do_capture` delegates image capture to the backend instead of calling `mss.mss().grab()` directly.
- Tests: `tests/test_capture_engine.py`, plus new macOS backend tests (mocked Quartz/CoreGraphics calls — no real macOS hardware needed to test).
- No change to session storage format, dedup logic, or the UI.
