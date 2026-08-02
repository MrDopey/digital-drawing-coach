## Context

`FeedbackPanel` (`src/drawing_coach/feedback_panel.py`) is a frameless, draggable `QWidget` with a fixed `setMinimumSize(380, 300)` and no explicit `resize()` call, so it opens at Qt's computed minimum size — too small to read a Full Critique response or a full-resolution overlay image comfortably.

The content area is a `QStackedWidget` holding a `QTextEdit` (text modes) and a `QLabel` (overlay image). It is added to the layout with `layout.addWidget(self._stack)` — no stretch factor, contradicting the project's own PyQt convention (`.claude/CLAUDE.md`: "Expanding widgets need a stretch factor... without it they don't grow when the dialog is resized"). The overlay pixmap is only rescaled inside `_render_current()`, which runs on `show_feedback()` / prev / next — there is no `resizeEvent` override, so dragging the panel's edge leaves the image at its original scaled size while the rest of the layout reflows around it.

Mode selection is a `QComboBox` (`_mode_combo`) read by `main_window._trigger_feedback` via `current_mode()`. Triggering itself lives entirely outside the panel: a "Get Feedback" button in the main window, a tray menu action, and a hotkey, all calling `main_window._trigger_feedback`. Nothing in the panel itself indicates that changing the mode doesn't do anything until one of those three external controls is used.

## Goals / Non-Goals

**Goals:**
- Open the panel at a size where both text and overlay-image content are legible without manual resizing.
- Make the overlay image track the panel's live size (rescale on resize, preserve aspect ratio).
- Replace the mode dropdown with a horizontal row of radio buttons showing all four modes at once.
- Add a right-aligned trigger button inside that same row, wired to the same feedback-request path `main_window._trigger_feedback` already uses.

**Non-Goals:**
- No change to `FeedbackEngine`, the LLM prompt/response formats, or the overlay annotation renderer.
- No change to the existing main-window "Get Feedback" button, tray menu action, or hotkey — they remain as additional, equivalent ways to trigger feedback.
- No change to session/history persistence or the separate History/Memory/Progress panels.

## Decisions

**Default size via `resize()`, not a larger `setMinimumSize()`.** Raising the minimum would force the floating panel to always occupy that footprint even when showing a short Quick Hint. Calling `self.resize(720, 560)` (or similar) in `__init__` after building the layout sets a comfortable *initial* size while leaving `setMinimumSize(380, 300)` as the floor a user can still shrink to.

**Stretch factor + `resizeEvent` for responsiveness, not `setScaledContents(True)`.** `setScaledContents(True)` on the `QLabel` would stretch the pixmap to fill the label ignoring aspect ratio, distorting the drawing. Instead:
- `layout.addWidget(self._stack, 1)` gives the content area the stretch factor per the project convention, so it (not the mode row or history row) absorbs resize deltas.
- Override `resizeEvent(self, event)` to re-invoke the existing scale-and-set-pixmap logic (factored out of `_render_current` into a small `_rescale_overlay()` helper) whenever the panel is resized and an overlay image is currently displayed. This reuses the existing `KeepAspectRatio` / `SmoothTransformation` scaling already proven in `_render_current`.

**Radio-button strip via `QButtonGroup` + `QRadioButton`, keeping `current_mode()`'s signature.** `main_window._trigger_feedback` calls `self._feedback_panel.current_mode()` and expects the same string keys (`quick_hint`, `full_critique`, `practice_exercise`, `overlay`) used in `MODE_LABELS`. A `QButtonGroup` holds one `QRadioButton` per entry in `MODE_LABELS`, each with its mode key stored via `setProperty("mode_key", key)` (Qt's button API has no built-in `itemData` equivalent). `current_mode()` is reimplemented to read the checked button's property instead of `QComboBox.currentData()` — callers outside the panel are unaffected. First radio (`quick_hint`) is checked by default, matching the combo box's prior default (first item).

**In-panel trigger button calls a panel-level callback, not a Qt signal.** The rest of the codebase (`hotkeys.on_trigger`, `detector.on_stuck`) already uses plain callback attributes rather than Qt signals for cross-component wiring (see `main_window.py`), so a `self.on_trigger_requested: Callable[[], None] | None = None` attribute on `FeedbackPanel`, invoked from the new button's `clicked` handler, matches the existing style. `main_window.__init__` sets `self._feedback_panel.on_trigger_requested = self._trigger_feedback` — identical to how `_trigger_feedback` is already wired to the standalone button, tray action, and hotkey, so no new trigger logic is introduced.

## Risks / Trade-offs

- [Resizing on every `resizeEvent` re-scales the pixmap on every intermediate frame while the user drags the edge, which is more work than the current render-only-on-content-change behavior] → Pillow/Qt scaling of a single screenshot-sized image is fast enough for interactive resize (existing precedent: `_render_current` already does this synchronously on every prev/next click); revisit only if profiling shows jank.
- [Adding a second "trigger feedback" control (in-panel button) alongside the existing main-window button/tray/hotkey could read as redundant] → Both call the same `_trigger_feedback` handler, so behavior stays single-sourced; the in-panel button exists specifically to make "change mode → press this" discoverable without leaving the panel, per the requesting feedback.
- [`QRadioButton` row is wider than the old combo box and may not fit the panel's minimum width of 380px for four labels] → Verify at implementation time; shrink label text (e.g. "Quick Hint" → "Quick") or wrap to two rows only if it doesn't fit, rather than pre-emptively redesigning.

## Open Questions

None — internal PyQt panel change with no external interfaces.
