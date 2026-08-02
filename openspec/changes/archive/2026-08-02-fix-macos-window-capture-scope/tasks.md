## 1. Backend protocol

- [x] 1.1 Add `capture_image(window_id: int | str) -> PIL.Image.Image | None` to the `WindowBackend` protocol in `window_manager.py`, and expose it on `WindowManager` as a thin passthrough (mirroring `get_window_rect`)

## 2. macOS backend implementation

- [x] 2.1 In `_backend_macos.py`, implement `MacOSBackend.capture_image` using `Quartz.CGWindowListCreateImage(Quartz.CGRectNull, Quartz.kCGWindowListOptionIncludingWindow, wid, imageOption)` scoped to the target window
- [x] 2.2 Convert the returned `CGImage` to a `PIL.Image` (read via `CGDataProvider`/`CFData`, strip row padding using bytes-per-row vs width, matching the approach `mss.darwin.MSSImplDarwin.grab` already uses)
- [x] 2.3 Return `None` when CoreGraphics yields no image (window closed, fully occluded by protected system UI, or minimized) so callers treat it the same as "window lost"

## 3. Windows/Linux backends (no behavior change)

- [x] 3.1 In `_backend_windows.py`, implement `capture_image` using the existing `get_window_rect` + `mss.grab()` rect approach, preserving current behavior exactly
- [x] 3.2 In `_backend_linux.py`, implement `capture_image` the same way as Windows

## 4. Capture engine integration

- [x] 4.1 In `capture_engine.py`, replace the direct `mss.mss().grab({...})` call in `_do_capture` with `self._manager.capture_image(self._target.id)`
- [x] 4.2 Keep the existing `get_window_rect` call for the "window lost" (`rect is None`) and zero-size checks before attempting capture
- [x] 4.3 Treat a `None` return from `capture_image` the same as a lost window (`on_window_lost` callback), same as the existing `rect is None` path

## 5. Tests

- [x] 5.1 Add unit tests for `MacOSBackend.capture_image` mocking `Quartz.CGWindowListCreateImage` and the CoreGraphics data-provider chain, verifying it's called with `kCGWindowListOptionIncludingWindow` and the target window ID (not a screen rect)
- [x] 5.2 Add a test asserting `MacOSBackend.capture_image` returns `None` when `CGWindowListCreateImage` yields no image
- [x] 5.3 Update `tests/test_capture_engine.py` to mock `manager.capture_image` instead of relying on a real `mss.mss()` call in `_do_capture` tests
- [x] 5.4 Add a regression test asserting `_do_capture` calls `manager.capture_image(target.id)` rather than instantiating `mss.mss()` directly

## 6. Documentation

- [x] 6.1 Update README.md with a developer-facing note that macOS window capture uses a direct CoreGraphics window-ID capture (not a screen-region grab), and why
- [x] 6.2 Update `.claude/CLAUDE.md` — add `MacOSBackend.capture_image` and its CoreGraphics/window-ID-scoped approach to the notes on the capture backend, if the memory/context notes there describe capture mechanics
- [x] 6.3 Review `openspec/config.yaml` for a recurring gap this spec reveals (e.g. platform-specific behavior requirements); propose changes only if a clear, recurring gap exists — high threshold, since this governs all future specs — reviewed, no recurring gap evident, no change made

## 7. Verification

- [x] 7.1 Run `uv run pytest` and confirm all tests pass — all pass except 3 pre-existing failures unrelated to this change (timing-flaky `test_stuck_detector.py` cooldown tests, and an LLM error-message wording mismatch in `test_diagnostics.py`); none touch files changed here
- [ ] 7.2 Manually verify on macOS hardware: select a drawing app window, overlap it with another app window, and confirm the captured frame shows only the drawing app's content — **not performed**: no macOS hardware available in this environment; requires manual verification before this change is considered fully validated
