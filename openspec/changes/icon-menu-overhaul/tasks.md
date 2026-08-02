## 1. Tray menu restore action

- [x] 1.1 In `main_window.py`, add a `_restore_main_window()` handler on `MainWindow` that calls `self.show()`, `self.raise_()`, and `self.activateWindow()`.
- [x] 1.2 In `_build_tray()`, replace the "Get Feedback" menu action with a "Show Drawing Coach" action wired to `_restore_main_window()`, as the first item in the menu.
- [ ] 1.3 Connect `self._tray.activated` to a handler that calls `_restore_main_window()` only when the reason is `QSystemTrayIcon.ActivationReason.DoubleClick`.

## 2. Remove duplicated tray shortcuts

- [ ] 2.1 In `_build_tray()`, remove the "Memory" (`_open_memory_viewer`) and "Progress" (`_open_progress_panel`) menu actions.
- [ ] 2.2 Confirm the resulting menu order is: Show Drawing Coach, separator, Pause/Resume Capture, Settings, separator, About, Quit.
- [ ] 2.3 Leave the main window's button row (Get Feedback, History, Memory, Progress, Settings buttons) untouched — `_open_memory_viewer` and `_open_progress_panel` stay as-is since the buttons still call them.

## 3. Tests

- [ ] 3.1 Add/update a test asserting the tray context menu no longer exposes Get Feedback, Memory, or Progress actions.
- [ ] 3.2 Add a test that invoking the restore action shows, raises, and activates the main window (covering both a hidden and an already-visible window).
- [ ] 3.3 Add a test that emitting `self._tray.activated` with `DoubleClick` restores the window, and that `Trigger`/`MiddleClick` reasons do not.

## 4. Documentation

- [ ] 4.1 Update `README.md` (developer-facing) to reflect the trimmed tray menu and the new "Show Drawing Coach" restore action, if the tray menu is documented there.
- [ ] 4.2 Update `.claude/CLAUDE.md` if this change implies any plausible update to its UI Conventions or feature description (review only — apply if a clear gap exists).
- [ ] 4.3 Review `openspec/config.yaml` and propose changes only if this spec reveals a clear, recurring gap in the current rules (high threshold — skip if nothing stands out).
- [ ] 4.4 Run `uv run pytest` and confirm all tests pass.
