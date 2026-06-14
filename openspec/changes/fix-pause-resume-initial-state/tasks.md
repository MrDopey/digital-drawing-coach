## 1. Implementation

- [ ] 1.1 Change initial `QPushButton` label from `"Pause"` to `"Start Capture"` (main_window.py line ~251)
- [ ] 1.2 Add `_update_capture_btn()` helper: sets button and tray action text based on `(self._capture.target is None, self._capture.paused)` — "Start Capture"/"Select Window", "Pause"/"Pause Capture", or "Resume"/"Resume Capture"
- [ ] 1.3 Update `_toggle_pause`: if `self._capture.target is None`, call `_select_window()` instead of pause/resume; call `_update_capture_btn()` after any state change
- [ ] 1.4 Call `_update_capture_btn()` from `_update_status` so the button stays in sync after window selection / window loss
- [ ] 1.5 Call `_update_capture_btn()` after `_select_window()` returns (window may have been selected or cancelled)

## 2. Tests

- [ ] 2.1 pytest-qt test: on `MainWindow` init with no target, button text is "Start Capture"
- [ ] 2.2 pytest-qt test: after `_capture.set_target(...)`, `_update_status` sets button to "Pause"
- [ ] 2.3 pytest-qt test: clicking "Start Capture" triggers `_select_window` (mock it to avoid opening a real dialog)

## 3. Documentation

- [ ] 3.1 Update `README.md` to describe the three button states (Start Capture → Pause → Resume)
- [ ] 3.2 Review `.claude/CLAUDE.md` — no new UI conventions; no changes needed
- [ ] 3.3 Review `openspec/config.yaml` — no recurring gap identified; no changes needed
- [ ] 3.4 Run `uv run pytest` and confirm all tests pass
