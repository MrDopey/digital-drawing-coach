## 1. macOS Permission Helpers

- [x] 1.1 Add `has_screen_recording_permission() -> bool` to `_backend_macos.py` using `CGWindowListCopyWindowInfo` via `ctypes` — returns `False` when the list is empty (permission denied)
- [x] 1.2 Add `has_input_monitoring_permission() -> bool` to `_backend_macos.py` using `AXIsProcessTrustedWithOptions(NULL)` via `ctypes` from the Accessibility framework
- [x] 1.3 Write pytest tests for both helpers mocking `ctypes` to verify the `True`/`False` branches

## 2. Diagnostics Module

- [x] 2.1 Create `src/drawing_coach/diagnostics.py` with a `CheckResult` dataclass: `name: str`, `passed: bool`, `message: str`, `hint: str`
- [x] 2.2 Implement `check_screen_capture() -> CheckResult` — dispatches to the macOS helper on `darwin`, attempts `mss` grab on Linux/Windows, returns appropriate pass/fail result with hint text per spec
- [x] 2.3 Implement `check_input_monitoring() -> CheckResult` — macOS only: calls `has_input_monitoring_permission()`; on other platforms returns `None` (skipped, not shown as a row)
- [x] 2.4 Implement `check_xdotool() -> CheckResult` — Linux only: uses `shutil.which("xdotool")`; on other platforms returns `None` (skipped)
- [x] 2.5 Implement `check_llm(config: LLMConfig) -> CheckResult` — returns fail if model is empty; otherwise attempts `litellm.completion` with "hi" and catches exceptions
- [x] 2.6 Implement `check_config_path() -> CheckResult` — checks `os.access(config_path().parent, os.W_OK)` then, if the file exists, attempts `json.loads(config_path().read_text())` to catch corruption; returns the resolved path in the message
- [x] 2.7 Implement `check_sessions_dir() -> CheckResult` — creates the directory if absent, then writes and deletes a probe file; returns the resolved path in the message
- [x] 2.8 Implement `check_pillow_png() -> CheckResult` — calls `Image.new("RGB", (1, 1)).save(io.BytesIO(), "PNG")` and catches any exception
- [x] 2.9 Add `CHECKS: list[Callable]` — the ordered list of check callables used to both submit to the executor and define display row order (skipped checks that return `None` are excluded at build time per platform)

## 3. Diagnostics Dialog Widget

- [x] 3.1 Add `DiagnosticsCoordinator(QThread)` inside `diagnostics.py` — accepts a `ThreadPoolExecutor` and a list of futures; iterates `as_completed(futures)` and emits `check_done = pyqtSignal(object)` per `CheckResult`; emits `all_done = pyqtSignal()` when the iterator exhausts
- [x] 3.2 Add `DiagnosticsDialog(QDialog)` — non-modal dialog with a `QVBoxLayout` pre-populated with one row per active check (status icon `QLabel` + name `QLabel` + message `QLabel`) and a "Re-run" `QPushButton`
- [x] 3.3 Implement `_start_checks()` in `DiagnosticsDialog` — resets all rows to "⏳ checking…", creates a `ThreadPoolExecutor(max_workers=len(checks))`, submits all check callables, starts `DiagnosticsCoordinator`; connects signals
- [x] 3.4 Implement `_on_check_done(result: CheckResult)` — looks up the row by `result.name`, updates with ✓ (green) or ✗ (red) icon and message; appends hint text in grey when `result.hint` is non-empty
- [x] 3.5 Override `closeEvent` to call `executor.shutdown(wait=False, cancel_futures=True)` and stop the coordinator thread before accepting close, preventing dangling threads

## 4. Settings Dialog Integration

- [x] 4.1 Import `DiagnosticsDialog` in `settings_dialog.py`
- [x] 4.2 Add a "Diagnostics…" `QPushButton` to the button row in `SettingsDialog.__init__` (left of Cancel/Save, separated by a spacer)
- [x] 4.3 Connect the button to `_open_diagnostics()` which instantiates `DiagnosticsDialog(config=self._config, parent=self.parent())` and calls `.show()`

## 5. Tests

- [x] 5.1 Write unit tests for each check function in `tests/test_diagnostics.py` — mock `mss`, `litellm`, `os.access`, `shutil.which`, `pathlib.Path.mkdir`/write, `json.loads`, and `PIL.Image` to cover pass and fail branches for all eight checks
- [x] 5.2 Write a `pytest-qt` test that opens `DiagnosticsDialog` with all checks mocked to pass and verifies all rows show ✓ after `all_done` fires
- [x] 5.3 Write a `pytest-qt` test that opens `DiagnosticsDialog` with the LLM check mocked to raise an exception and verifies that row shows ✗ with hint text

## 6. Documentation

- [x] 6.1 Update `README.md` to mention the Diagnostics button under the "Getting Started" or "Troubleshooting" section, listing all checks and where to find them

## 7. Verification

- [x] 7.1 Run `uv run pytest` and confirm all tests pass
