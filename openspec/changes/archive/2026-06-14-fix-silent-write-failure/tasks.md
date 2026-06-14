## 1. CaptureEngine — error callback and logging

- [x] 1.1 Add `on_write_error: Callable[[Path, Exception], None] | None = None` attribute to `CaptureEngine.__init__`
- [x] 1.2 In `_write_frame` except block, add `_log.warning("Frame write failed: %s", path, exc_info=True)` and call `self.on_write_error(path, exc)` if set

## 2. MainWindow — status bar and hover popup

- [x] 2.1 Add a `QStatusBar` to `MainWindow` via `self.statusBar()` in `_build_ui`
- [x] 2.2 Create a permanent `QLabel` inside the status bar with `TextSelectableByMouse | TextSelectableByKeyboard` interaction flags for the write-failure warning
- [x] 2.3 Implement `_WriteErrorPopup` — a `QFrame` (borderless, `ToolTip` window flag) containing a read-only `QPlainTextEdit` with `TextSelectableByMouse`, positioned above the status bar on `enterEvent`/hidden on `leaveEvent` of the warning label
- [x] 2.4 Wire `engine.on_write_error = self._on_write_error` in the place where `on_frame_captured` is wired; implement `_on_write_error(path, exc)` to set the status bar warning text and update the popup body
- [x] 2.5 In `_on_frame_captured` (or equivalent success handler), clear the status bar warning when the path is not None

## 3. Tests

- [x] 3.1 Add a pytest unit test that patches `PIL.Image.Image.save` to raise `OSError`, calls `CaptureEngine._write_frame`, and asserts the WARNING is logged with `caplog`
- [x] 3.2 Add a pytest unit test that a registered `on_write_error` callback is called with the correct path and exception when `img.save()` raises
- [x] 3.3 Add a pytest-qt test that verifies the status bar warning label appears after `on_write_error` fires and clears after `on_frame_captured` fires with a non-None path

## 4. Documentation

- [x] 4.1 Update README.md: note that frame write failures appear in the status bar and that the sessions directory must be writable
- [x] 4.2 Review `.claude/CLAUDE.md` — no new conventions needed; this is a standard PyQt6 status bar + callback pattern
- [x] 4.3 Review `openspec/config.yaml` — no changes needed; the gap was a one-off omission

## 5. Verification

- [x] 5.1 Run `uv run pytest` and confirm all tests pass
