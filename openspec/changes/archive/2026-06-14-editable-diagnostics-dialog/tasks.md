## 1. Make message labels selectable

- [x] 1.1 In `DiagnosticsDialog.__init__`, add `setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)` to each `msg_lbl` after creation
- [x] 1.2 Add `setMinimumWidth(1)` to each `msg_lbl` (CLAUDE.md requirement for word-wrapped labels in grid layouts)

## 2. Copy Report button

- [x] 2.1 Add a `list[CheckResult]` instance variable `_completed_results` to `DiagnosticsDialog`, reset to `[]` at the start of `_start_checks`
- [x] 2.2 In `_on_check_done`, append the received `CheckResult` to `_completed_results`
- [x] 2.3 Add a `_copy_report_btn` (`QPushButton("Copy Report")`) to the button row in `__init__`, disabled by default
- [x] 2.4 Connect `_copy_report_btn.clicked` to a `_copy_report` method that formats results as plain text and calls `QApplication.clipboard().setText(...)`
- [x] 2.5 Enable `_copy_report_btn` in the `all_done` lambda alongside `_rerun_btn`; disable it again at the start of `_start_checks`
- [x] 2.6 Implement `_copy_report`: iterate `_completed_results`, emit `[✓] Name — message` or `[✗] Name — message\n      Hint: <hint>` lines

## 3. Initial dialog height

- [x] 3.1 Wrap `rows_widget` in a `QScrollArea` (`setWidgetResizable(True)`, `setFrameShape(QFrame.Shape.NoFrame)`) and add it to the layout with stretch factor 1 so it expands on resize
- [x] 3.2 Call `self.adjustSize()` at the end of `__init__` so the dialog opens sized to fit all rows rather than the Qt default minimum

## 4. Tests

- [x] 4.1 Add a test that each `msg_lbl` in a freshly constructed `DiagnosticsDialog` has `TextSelectableByMouse` in its `textInteractionFlags()`
- [x] 4.2 Add a test that after `all_done`, `_copy_report_btn` is enabled
- [x] 4.3 Add a test that `_copy_report` copies the correct plain-text to the clipboard (mock `QApplication.clipboard()`)

## 5. Documentation

- [x] 5.1 Review `README.md` for any developer notes about the diagnostics dialog and update if needed
- [x] 5.2 Review `.claude/CLAUDE.md` — add a note that `QLabel`s with `setWordWrap(True)` in grids also need `setTextInteractionFlags` set if the text must be selectable
- [x] 5.3 Review `openspec/config.yaml` and propose changes only if the spec reveals a clear, recurring gap in the current rules
- [x] 5.4 Run `uv run pytest` and confirm all tests pass
