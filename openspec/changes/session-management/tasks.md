## 1. Data Layer — meta.json name field

- [ ] 1.1 Add `name` field to `_write_meta` in `capture_engine.py`, defaulting to timestamp label `Session DD Mon YYYY, HH:MM`
- [ ] 1.2 Add `read_session_name(session_dir)` and `write_session_name(session_dir, name)` helpers (read `meta.json`, fall back to timestamp label if `name` absent)
- [ ] 1.3 Add `load_session(session_dir: Path)` and `new_session()` public methods to `CaptureEngine`; `load_session` stops capture, flushes, switches dir, reloads frames, restarts capture

## 2. Session Picker Dialog

- [ ] 2.1 Create `session_picker_dialog.py` with `SessionPickerDialog(QDialog)` listing sessions in reverse-chronological order
- [ ] 2.2 Each row shows: session name, start date/time, 120×80 thumbnail (`QLabel` with scaled pixmap from last frame PNG, or grey placeholder if no frames)
- [ ] 2.3 Expand thumbnail to 360×240 on hover (floating `QLabel` tooltip overlay)
- [ ] 2.4 Implement Resume button (default action, also triggered by double-click) — returns `('resume', session_dir)`
- [ ] 2.5 Implement New Session button — returns `('new', None)`
- [ ] 2.6 Implement Delete button with confirmation dialog; removes session dir from disk and refreshes list
- [ ] 2.7 Closing the dialog without selecting returns `('quit', None)`
- [ ] 2.8 Dialog is skipped entirely (returns `('new', None)` immediately) when `sessions_dir()` has no valid session directories

## 3. Launch Flow

- [ ] 3.1 Update `__main__.py` to show `SessionPickerDialog` before constructing `MainWindow`; handle `resume`/`new`/`quit` outcomes
- [ ] 3.2 Pass chosen `session_dir` (or `None` for new) into `CaptureEngine` constructor or via `load_session` / `new_session`

## 4. Inline Session Naming

- [ ] 4.1 In `SessionPickerDialog`, make the name label double-click editable (inline `QLineEdit`); save on Enter/focus-loss; restore timestamp label if left empty
- [ ] 4.2 Add pencil icon button alongside each name label as an alternative trigger for inline edit

## 5. Main Window — Title Bar & Sessions Menu

- [ ] 5.1 Update `MainWindow.setWindowTitle` to show `Drawing Coach — <session name>`; refresh on session load and rename
- [ ] 5.2 Add a `Sessions` menu to the menu bar listing: active session (greyed), all other sessions (newest first), separator, New Session action
- [ ] 5.3 Populate Sessions menu dynamically when opened; connect each entry to `CaptureEngine.load_session`
- [ ] 5.4 Add session rename widget in main window (e.g. editable label in toolbar or header area); save on commit, update title bar

## 6. Tests

- [ ] 6.1 Unit tests for `read_session_name` / `write_session_name` helpers (name present, name absent, empty name)
- [ ] 6.2 Unit test for `_write_meta` — verify `name` field is written with correct format
- [ ] 6.3 pytest-qt test for `SessionPickerDialog`: empty sessions dir skips dialog; sessions listed in reverse-chron order; delete removes dir

## 7. Documentation

- [ ] 7.1 Update `README.md` with a note on session management (picker on launch, renaming, in-app switching)
- [ ] 7.2 Review `.claude/CLAUDE.md` — no plausible changes implied by this spec (no new UI conventions introduced)
- [ ] 7.3 Review `openspec/config.yaml` — no recurring gap identified; no changes needed
- [ ] 7.4 Run `uv run pytest` and confirm all tests pass
