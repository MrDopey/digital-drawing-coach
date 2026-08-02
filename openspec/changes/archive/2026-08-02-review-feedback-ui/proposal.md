## Why

The feedback panel's default window is too small to read feedback comfortably, and in Overlay mode the annotated screenshot dominates the layout and does not rescale when the user resizes the panel — the image can crowd out the explanatory text entirely. Separately, the mode selector is a plain dropdown with no visible action to trigger feedback, so it's unclear to users when/how a feedback request is actually fired.

## What Changes

- Increase the feedback panel's default window size so both the image (in Overlay mode) and text feedback are comfortably visible on open.
- Make the panel's content area responsive: the overlay image SHALL rescale (preserving aspect ratio) whenever the panel is resized, instead of only rescaling on next render.
- Replace the mode `QComboBox` with a horizontal strip of radio buttons (Quick Hint / Full Critique / Practice Exercise / Overlay) so the active mode is always visible at a glance.
- Add a right-aligned "Get Feedback" trigger button in the same row as the mode radio buttons, so selecting a mode and firing a feedback request happens from one clearly-labeled control inside the panel itself.

## Capabilities

### Modified Capabilities
- `feedback-modes`: mode selection UI changes from a dropdown to a horizontal radio-button strip with an explicit in-panel trigger button; panel display requirements gain responsive resizing and a larger default size.

## Impact

- `src/drawing_coach/feedback_panel.py`: mode selector widget, layout stretch factors, resize handling, new trigger button/signal.
- `src/drawing_coach/main_window.py`: `_trigger_feedback` wiring — the existing "Get Feedback" button/tray/hotkey paths continue to work, and the panel's own trigger button connects to the same handler.
