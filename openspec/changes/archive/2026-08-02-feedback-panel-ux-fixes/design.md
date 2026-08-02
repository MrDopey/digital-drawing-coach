## Context

`FeedbackPanel` (`src/drawing_coach/feedback_panel.py`) is a frameless `QWidget` window titled `"Drawing Coach — Feedback"`. Today there is exactly one code path that shows it: `MainWindow._trigger_feedback` (`main_window.py:521-562`), which is wired to the main toolbar's "Get Feedback" button (`main_window.py:281-282`), the tray menu's "Get Feedback" action (`main_window.py:316`), the hotkey (`main_window.py:416` → `StuckDetector.manual_trigger`), and automatic stuck detection (`main_window.py:415`, `stuck_detector.py`). `_trigger_feedback` both calls `self._feedback_panel.show_loading()` (which shows the window) and kicks off `FeedbackEngine.request_feedback(...)` on a background thread — opening and requesting are the same action, with no way to do one without the other.

Inside the panel, overlay images and feedback text are mutually exclusive: a `QStackedWidget` (`feedback_panel.py:90-99`) shows either the `QTextEdit` (index 0) or a plain `QLabel` overlay image (index 1), never both. When an overlay is shown, the full response text is discarded down to a 120-character truncated notice (`_overlay_notice`, `feedback_panel.py:103-104, 202-207`) instead of being shown in full. There is no `QSplitter` anywhere in the codebase.

## Goals / Non-Goals

**Goals:**
- Rename the panel to "Feedback Management" (window title, main toolbar button, tray menu item).
- Separate "open the panel" from "request feedback": opening SHALL NOT call the LLM; a request only fires from an explicit control.
- Show the overlay image and the feedback text simultaneously, in a user-resizable vertical split.
- Ensure feedback content — including overlay images larger than the visible area — can be scrolled/viewed in full.
- Allow the user to zoom in/out on the overlay image within the top pane.

**Non-Goals:**
- Changing the mode selector from a `QComboBox` to the radio-button strip described in the `feedback-modes` spec's existing (already-drifted, pre-existing) requirement text — out of scope for this change.
- Changing automatic stuck-detection behavior (`StuckDetector.on_stuck` still calls straight through to a full request) or the hotkey's manual-trigger behavior — both are existing, intentional "explicit/proactive request" paths, not the "opening" action this change targets, and are left unchanged.
- Any change to `FeedbackEngine`, prompt construction, or LLM response parsing.

## Decisions

**1. Extract request logic out of the button handler.**
`MainWindow._trigger_feedback` is split into two methods:
- `_open_feedback_panel()` — just `self._feedback_panel.show(); self._feedback_panel.raise_()`. Wired to the toolbar button and tray menu item (both renamed to "Feedback Management").
- `_request_feedback(mode: str)` — the existing show-loading + background-thread LLM call logic, unchanged in behavior. Wired to: `StuckDetector.on_stuck` (auto-trigger, unchanged), the hotkey path (unchanged), and a new signal emitted by `FeedbackPanel` when its in-panel "Request Feedback" button is clicked.

Alternative considered: keep a single method and gate the API call behind a dialog-confirmation. Rejected — adds friction to the already-explicit hotkey/tray/stuck-detection paths, which don't need gating; only the panel's own new button needs to be the sole "opening implies nothing" entry point.

**2. Add an explicit in-panel trigger button.**
`FeedbackPanel` gains a `feedback_requested = pyqtSignal(str)` signal and a "Request Feedback" `QPushButton` next to the existing mode `QComboBox` (`feedback_panel.py:74-81` mode row). Clicking it emits `feedback_requested` with `self.current_mode()`; `MainWindow` connects this to `_request_feedback`. This also fulfils the `feedback-modes` spec's existing (previously unimplemented) requirement for a mode-row trigger button, so the delta spec formalizes actual button placement rather than a radio-strip redesign.

**3. Replace the `QStackedWidget` with a `QSplitter(Qt.Orientation.Vertical)`.**
Two panes, both children of the splitter, both always present in the layout:
- Top pane: `self._image_label` wrapped in a `QScrollArea` (`setWidgetResizable=True`), shown only when the current history entry has an overlay image; otherwise the top pane is collapsed to zero height via `splitter.setSizes([0, ...])` so text-only responses show just the bottom pane.
- Bottom pane: `self._text_edit`, always populated with `resp.text` (full text, not truncated) regardless of mode. The 120-char `_overlay_notice` label is removed — the splitter's bottom pane replaces it.

The splitter's initial sizes default to roughly 60/40 (image/text) when an overlay is present, and the user can drag the handle to any proportion afterward; the panel remembers nothing across sessions (no persistence requirement was requested).

Alternative considered: keep the stack and add a toggle button to flip between image/text. Rejected — doesn't satisfy "show both, resizable," which is what was asked for.

**4. Scrollable overlay image.**
Wrapping `self._image_label` in a `QScrollArea` means large overlay images can be viewed at a size larger than the current pane (scrolled) instead of being force-downscaled to fit, addressing "the feedback cannot be seen particularly well." The existing `pixmap.scaled(...)` downscale-to-fit call (`feedback_panel.py:192-199`) is replaced with rendering the pixmap at its native resolution (or a fixed reasonable max) inside the scroll area, so detail isn't lost to shrinking.

**5. Zoom controls for the overlay image.**
`FeedbackPanel` gains a `_zoom_factor: float` (default `1.0`, meaning the native-resolution rendering from Decision 4). A small control row above the image scroll area holds "−" / "Reset" / "+" `QPushButton`s plus a live percentage `QLabel`; `Ctrl+Wheel` while the mouse is over the image also adjusts zoom, for users who prefer it. Each zoom step multiplies/divides `_zoom_factor` by `1.25`, clamped to a `0.25`–`4.0` range. Zooming re-renders `self._image_label`'s pixmap from the stored PIL overlay image (`self._overlay_images[...]`) at `native_size * _zoom_factor` — never re-scaling an already-scaled `QPixmap` — and the surrounding `QScrollArea` picks up the new content size automatically (`setWidgetResizable=True` still applies to the scroll area itself, not the label's pixmap size). "Reset" sets `_zoom_factor` back to `1.0`. `_zoom_factor` is reset to `1.0` whenever `_show_prev`/`_show_next` change `self._history_idx`, so a zoomed-in view doesn't carry over to an unrelated image.

Alternative considered: trackpad pinch-to-zoom gesture. Rejected — no `QGesture` wiring exists anywhere else in this codebase, and buttons + `Ctrl+Wheel` cover the ask with far less complexity.

## Risks / Trade-offs

- [Risk] Splitting `_trigger_feedback` changes which code path the main button/tray item exercise → could regress the existing "trigger feedback identically from button/tray/hotkey/panel" scenario in `feedback-modes` spec. → Mitigation: the delta spec explicitly documents the new split (open vs. request) so the scenario is updated, not silently broken; the hotkey and stuck-detection paths keep calling the full request behavior unchanged, so those two scenarios still hold.
- [Risk] Collapsing the image pane to zero height for text-only responses could look like a UI glitch if the splitter handle is still draggable to reveal empty space. → Mitigation: hide the image pane's container widget (not just resize to 0) when no overlay image exists for the current history entry, so there's no empty draggable region.
- [Risk] Users who relied on clicking "Get Feedback" for instant results now need one extra click (open, then request) the first time. → Mitigation: this is the explicit intent of the request; documented in the proposal's "What Changes."
- [Risk] The base `feedback-modes` spec has a pre-existing requirement that the overlay image "rescales to fit" whenever the panel is resized. Decision 4/5's native-resolution + manual-zoom rendering deliberately supersedes this — an image at a fixed zoom level does not auto-rescale on resize; the pane just shows more/less of it via scrolling. → Mitigation: the `feedback-modes` delta spec's "Feedback is displayed in a non-intrusive panel" requirement replaces the old "rescales when resized" scenario with a "keeps its zoom level when resized" scenario, so this is a documented, intentional behavior change rather than a silent regression.
- [Risk] `FeedbackPanel.mousePressEvent`/`mouseMoveEvent` (`feedback_panel.py:228-239`) implement whole-window dragging for the frameless panel; a `QScrollArea`/`QLabel` child widget already intercepts mouse events for scrolling before this change, and the new zoom buttons and `Ctrl+Wheel` handling add more child-widget event consumption in the same area. → Mitigation: dragging the panel by its title bar row (`feedback_panel.py:62-71`) is unaffected since that row is outside the image pane; no behavior change needed there, just confirm during manual verification that zoom/scroll interactions don't accidentally move the window.

## Migration Plan

No data migration. This is a UI-only change within a single session's runtime state (`FeedbackPanel` history list, in-memory only). Rollout is a normal code change + release; no feature flag needed since behavior is opt-out-free and immediately visible.

## Open Questions

None outstanding — stuck-detection/hotkey auto-request behavior is intentionally left unchanged (see Non-Goals).
