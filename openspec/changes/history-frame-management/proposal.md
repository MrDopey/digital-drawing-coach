## Why

The history panel is read-only: users cannot remove unwanted frames (blurry captures, accidental screenshots) from the buffer before sending feedback. They also have no visibility into which frames the LLM will actually receive, making the `lookback_frames` setting opaque and hard to reason about.

## What Changes

- Each frame thumbnail in the history panel gains a **delete/dismiss button** (visible on hover) that removes the frame from the in-memory buffer so it is excluded from the next LLM request
- A **visual lookback indicator** highlights the frames that *will* be sent to the LLM (the latest frame + up to `lookback_frames` prior) with a coloured border or badge, updating live as frames are added or deleted

## Capabilities

### New Capabilities
- `frame-deletion`: Per-frame delete button in the history panel that removes a frame from the capture buffer
- `lookback-indicator`: Visual highlight on history panel thumbnails showing which frames will be included in the next LLM request

### Modified Capabilities
- `screenshot-capture`: `CaptureEngine` must expose a `remove_frame` method so the UI can delete a frame from the in-memory buffer (no disk deletion required)

## Impact

- `src/drawing_coach/history_panel.py` — UI changes for delete buttons and lookback highlighting
- `src/drawing_coach/capture_engine.py` — new `remove_frame(frame: CapturedFrame)` method
- `src/drawing_coach/main_window.py` — wire delete callback from history panel to `CaptureEngine.remove_frame`; refresh lookback indicator on new captures
- No new dependencies
