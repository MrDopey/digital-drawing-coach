## Why

The delete button in each Session History row is a bare 20×20 `QPushButton("×")` with no styling — it looks visually out of place next to the app's other buttons (e.g. in `feedback_panel.py`, which uses rounded, themed buttons with a hover state) and is fiddly to hit. Rows also give no hover feedback beyond the delete button appearing, making it harder to tell which row is under the cursor before clicking.

## What Changes

- Restyle the per-row delete button to match the app's button conventions (rounded corners, themed background/hover color, adequate padding/size) instead of the current unstyled 20×20 "×" button.
- Add a hover highlight to each history row: the row's background changes color when the mouse is over it, independent of and in addition to the existing delete-button-reveal and lookback-window left-border indicator.

## Capabilities

### New Capabilities
- `history-panel-theming`: Visual styling of Session History rows — restyled delete button and row hover-highlight behavior.

### Modified Capabilities
(none — `history-panel-open-image` covers interaction behavior, not visual styling, and is unaffected)

## Impact

- `src/drawing_coach/history_panel.py`: `_FrameRowWidget` only (delete button styling, hover-highlight logic layered alongside existing `set_highlighted` lookback border). `HistoryPanel`'s own dialog chrome is unchanged.
- No changes to `CaptureEngine`, `CapturedFrame`, or any non-UI logic.
