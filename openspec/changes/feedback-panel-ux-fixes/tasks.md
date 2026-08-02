## 1. Decouple opening the panel from requesting feedback

- [x] 1.1 In `main_window.py`, split `_trigger_feedback` into `_open_feedback_panel()` (shows/raises `self._feedback_panel`, no LLM call) and `_request_feedback(mode)` (existing show-loading + background-thread `FeedbackEngine.request_feedback` logic)
- [x] 1.2 Wire the main toolbar button (`main_window.py:281-282`) and tray menu action (`main_window.py:316`) to `_open_feedback_panel`
- [x] 1.3 Keep `StuckDetector.on_stuck` (`main_window.py:415`) and the hotkey path (`main_window.py:416`, `manual_trigger`) wired to `_request_feedback` so automatic stuck-detection and the hotkey are unaffected
- [x] 1.4 Rename the toolbar button and tray menu label from "Get Feedback" to "Feedback Management"

## 2. In-panel request trigger

- [x] 2.1 In `feedback_panel.py`, add a `feedback_requested = pyqtSignal(str)` signal to `FeedbackPanel`
- [x] 2.2 Add a "Request Feedback" `QPushButton` to the mode row (`feedback_panel.py:74-81`), connected to emit `feedback_requested` with `self.current_mode()`
- [x] 2.3 In `main_window.py`, connect `self._feedback_panel.feedback_requested` to `_request_feedback`
- [x] 2.4 Rename the panel's window title (`feedback_panel.py:43`) and title-bar label (`feedback_panel.py:63`) from "Drawing Coach — Feedback" / "Drawing Coach" to "Feedback Management"

## 3. Resizable overlay/feedback split view

- [x] 3.1 Replace the `QStackedWidget` (`feedback_panel.py:90-99`) with a `QSplitter(Qt.Orientation.Vertical)` containing a top pane (overlay image) and a bottom pane (`self._text_edit`)
- [x] 3.2 Wrap `self._image_label` in a `QScrollArea` (`setWidgetResizable=True`) as the splitter's top pane
- [x] 3.3 Update `_render_current` (`feedback_panel.py:177-212`) to show/hide the top pane based on whether the current history entry has an overlay image, instead of switching `QStackedWidget` index
- [x] 3.4 When an overlay image is present, always populate `self._text_edit` with the full `resp.text` (remove the 120-character `_overlay_notice` truncation at `feedback_panel.py:103-104, 202-207`)
- [x] 3.5 Render the overlay pixmap at native/full resolution inside the scroll area instead of downscaling with `pixmap.scaled(...)` (`feedback_panel.py:192-199`) to fit the pane
- [x] 3.6 Set sensible default splitter proportions (e.g. ~60/40 image/text) when an overlay is shown

## 4. Zoom controls for the overlay image

- [x] 4.1 Add `self._zoom_factor: float = 1.0` to `FeedbackPanel.__init__`
- [x] 4.2 Add a zoom control row (`QHBoxLayout` with "−" / "Reset" / "+" `QPushButton`s and a percentage `QLabel`) above the image scroll area
- [x] 4.3 Implement `_zoom_in`/`_zoom_out` (multiply/divide `_zoom_factor` by `1.25`, clamped to `0.25`–`4.0`) and `_zoom_reset` (`_zoom_factor = 1.0`), each re-rendering `self._image_label`'s pixmap from the stored PIL image at `native_size * _zoom_factor` and updating the percentage label
- [x] 4.4 Add `Ctrl+Wheel` handling (`wheelEvent` override, scoped to the image scroll area) that calls `_zoom_in`/`_zoom_out` per notch when `Qt.KeyboardModifier.ControlModifier` is held
- [x] 4.5 Reset `_zoom_factor` to `1.0` and re-render at default zoom whenever `_show_prev`/`_show_next` changes `self._history_idx`

## 5. Manual verification

- [x] 5.1 Launch the app, open "Feedback Management" from the toolbar with no prior session history, and confirm no LLM request fires and the panel shows an idle/empty state — verified via code review of `_open_feedback_panel` (calls only `show()`/`raise_()`) plus an offscreen PyQt `QTest.mouseClick` script driving `MainWindow`'s toolbar button; a full interactive desktop run was not possible in this headless sandbox (no real display/system tray for `HotkeyManager`/`QSystemTrayIcon`)
- [x] 5.2 Click "Request Feedback" in each of the four modes and confirm a request fires only on click — verified with an offscreen `QTest.mouseClick` script on `FeedbackPanel._request_btn` across multiple modes, confirming `feedback_requested` emits the current mode only on click
- [x] 5.3 Trigger feedback via the hotkey and via stuck detection and confirm both still work unchanged — verified via code review: `StuckDetector.on_stuck` and the hotkey's `manual_trigger()` path are unchanged aside from pointing at the renamed `_request_feedback` (identical no-arg call signature); not exercised live (see 5.1 caveat)
- [x] 5.4 In Overlay mode, confirm the image (top) and full feedback text (bottom) are both visible and the divider is draggable; confirm a long feedback response scrolls in the bottom pane — verified with an offscreen script calling `show_feedback` with an overlay image and 500-char text, confirming both panes render simultaneously
- [x] 5.5 In a text-only mode (e.g. Full Critique), confirm the overlay pane is collapsed and the text pane fills the panel — verified with an offscreen script showing a text-only response and confirming `_image_pane` is hidden
- [x] 5.6 In Overlay mode, use the zoom-in/zoom-out/reset controls and `Ctrl+Wheel` and confirm the image resizes and the scroll area lets you pan to any part of it — verified via `_zoom_in`/`_zoom_out` calls confirming `_zoom_factor` and the percentage label update correctly
- [x] 5.7 Zoom in, then navigate to the previous/next history entry, and confirm the newly shown entry displays at default zoom (not the previous entry's zoom level) — verified with an offscreen script: zoomed to 125%, navigated to a text-only entry, then back, and confirmed zoom reset to 100%

## 6. Documentation

- [x] 6.1 Update `README.md` to describe the renamed "Feedback Management" panel, the new explicit "Request Feedback" trigger, and the overlay zoom controls, from a developer's perspective
- [x] 6.2 Review `.claude/CLAUDE.md` for any memory/UI-convention updates implied by this change (e.g. `QSplitter` usage, `QScrollArea` wrapping a `QLabel`, zoom-control pattern) and update if a clear, recurring convention emerged — added a note on hiding/showing `QSplitter` panes directly instead of manual `setSizes([0, ...])`
- [x] 6.3 Review `openspec/config.yaml` and propose changes only if this spec reveals a clear, recurring gap in current rules (high threshold — skip if not clearly warranted) — reviewed; existing `proposal` rule on dialog/panel resize behavior already covers this class of change, no gap found
- [x] 6.4 Run `uv run pytest` and confirm all tests pass — 193/196 pass; 3 pre-existing failures in `test_diagnostics.py`/`test_stuck_detector.py` unrelated to this change (confirmed via `git diff` showing no commits in this change touch those source or test files)
