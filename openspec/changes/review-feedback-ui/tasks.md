## 1. Panel sizing and responsiveness

- [x] 1.1 In `FeedbackPanel.__init__`, call `self.resize(...)` with a default size large enough to show a Full Critique response and a full overlay image comfortably, leaving `setMinimumSize(380, 300)` as the floor.
- [x] 1.2 Add a stretch factor to the content stack: `layout.addWidget(self._stack, 1)`.
- [x] 1.3 Extract the overlay pixmap scale-and-set logic currently inline in `_render_current` into a `_rescale_overlay()` helper that re-scales the currently displayed overlay image (if any) to the stack's current size, preserving aspect ratio.
- [ ] 1.4 Override `resizeEvent` on `FeedbackPanel` to call `_rescale_overlay()` after the base implementation, so the overlay image tracks live panel resizes.

## 2. Mode selector as a radio-button strip

- [ ] 2.1 Replace `self._mode_combo` (`QComboBox`) with a `QButtonGroup` of `QRadioButton`s, one per `MODE_LABELS` entry, laid out horizontally in the existing mode row; store each mode's key via `setProperty("mode_key", key)`.
- [ ] 2.2 Check the first radio button (`quick_hint`) by default to preserve the combo box's prior default selection.
- [ ] 2.3 Reimplement `current_mode()` to return the checked radio button's `mode_key` property instead of `QComboBox.currentData()`.

## 3. In-panel feedback trigger

- [ ] 3.1 Add a right-aligned "Get Feedback" `QPushButton` to the mode row.
- [ ] 3.2 Add an `on_trigger_requested: Callable[[], None] | None = None` attribute to `FeedbackPanel`; connect the new button's `clicked` signal to invoke it if set.
- [ ] 3.3 In `main_window.py`, set `self._feedback_panel.on_trigger_requested = self._trigger_feedback` alongside the panel's construction, so the in-panel button triggers feedback identically to the existing button/tray/hotkey paths.

## 4. Tests

- [ ] 4.1 Add `tests/test_feedback_panel.py` (pytest-qt, following the pattern in `tests/test_history_panel.py`) covering: default size is larger than the old minimum, `current_mode()` returns the correct key after selecting each radio button, the trigger button invokes `on_trigger_requested`, and resizing the panel while an overlay image is shown rescales the pixmap without changing its aspect ratio.

## 5. Documentation

- [ ] 5.1 Update `README.md` from a developer's perspective to describe the panel's new default size, radio-button mode strip, and in-panel trigger button.
- [ ] 5.2 Review `.claude/CLAUDE.md`'s "UI Conventions (PyQt6)" section and add a line about overlay/image content needing a `resizeEvent`-driven rescale when a stretch-factored widget contains a scaled pixmap, since this wasn't previously called out and this change fixes a bug caused by its absence.
- [ ] 5.3 Review `openspec/config.yaml` and propose changes only if this spec reveals a clear, recurring gap in the current rules; otherwise leave unchanged.

## 6. Verification

- [ ] 6.1 Run `uv run pytest` and confirm all tests pass.
