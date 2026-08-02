## 1. Pause/Resume disabled-until-selected behavior

- [ ] 1.1 In `main_window.py` `_update_status()`, set `self._pause_btn.setEnabled(...)` and `self._tray_pause_action.setEnabled(...)` based on `self._capture.target is not None`, in addition to the existing label logic.
- [ ] 1.2 In `_build_ui()`, after creating `_pause_btn` (and after `_tray_pause_action` is created in `_build_tray()`), ensure the initial state is disabled with the "Resume" label before any window is selected (either by calling `_update_status()` once construction of both widgets is complete, or by setting the disabled state explicitly at creation time).
- [ ] 1.3 In `_on_window_lost()`, ensure the disabled/paused state is applied (already calls `_update_status()`; confirm it now disables the control per 1.1).
- [ ] 1.4 In `_open_app_selection()`, confirm the existing `_update_status()` call after `set_target()` re-enables the control (should fall out of 1.1 automatically).

## 2. Tests

- [ ] 2.1 Add/extend a `pytest-qt` test in `tests/` asserting the pause button and tray action are disabled and show "Resume" immediately after `MainWindow` construction, before any window is selected.
- [ ] 2.2 Add a test asserting the pause button becomes enabled after a window is selected (simulate `_capture.set_target(...)` + the selection flow, or call `_update_status()` directly with a target set).
- [ ] 2.3 Add a test asserting the pause button returns to disabled after `_on_window_lost()` fires.

## 3. Documentation

- [ ] 3.1 Update `README.md` to note that the Pause/Resume control is disabled until a drawing window is selected.
- [ ] 3.2 Review `.claude/CLAUDE.md` for any memory.md implications from this change; no update expected since this is a UI-state fix with no new architecture, config, or tooling surface.
- [ ] 3.3 Review `openspec/config.yaml` for a recurring gap surfaced by this spec; no change expected unless a clear, recurring pattern is found.
- [ ] 3.4 Run `uv run pytest` and confirm all tests pass.
