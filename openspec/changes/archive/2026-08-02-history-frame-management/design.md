## Context

`HistoryPanel` is currently a `QDialog` that receives a snapshot `list[CapturedFrame]` at construction time and is read-only. `CaptureEngine` owns the `_buffer` deque. `FeedbackEngine.request_feedback` calls `get_frames()` and then slices `frames[-(lookback + 1):]` to select the window sent to the LLM. The history panel has no callback mechanism back to the engine.

## Goals / Non-Goals

**Goals:**
- Delete button per thumbnail, visible on hover, removes the frame from the live buffer
- Coloured border/badge on thumbnails that fall within the current lookback window
- Indicator updates automatically when frames are captured or deleted

**Non-Goals:**
- Deleting frames from disk (only in-memory removal)
- Undo / restore of deleted frames
- Changing the lookback window size from the history panel

## Decisions

### 1. History panel becomes a persistent widget, not a one-shot dialog

Currently the panel is constructed fresh each time from a snapshot list. To support live updates (new captures refreshing the lookback indicator, delete removing a row), the panel needs to stay open and react to events.

The panel will be refactored to a `QWidget` (embedded or docked) or remain a `QDialog` but accept a live `CaptureEngine` reference and connect to a `frames_changed` signal.

**Alternative:** Keep snapshot approach, re-open panel each time — poor UX, deleted frames reappear on next open.

### 2. `CaptureEngine` emits a `frames_changed` PyQt signal

A `pyqtSignal()` fires after any mutation of `_buffer` (append, remove). `HistoryPanel` connects to it and re-renders. This decouples the engine from the panel.

**Alternative:** Polling timer — adds latency and unnecessary CPU use.

### 3. `CaptureEngine.remove_frame(frame)` removes by identity

Uses `list(self._buffer).index(frame)` (identity, not equality) or rebuilds the deque excluding the target. O(n) is acceptable for typical buffer sizes (≤ 100 frames). Does NOT delete the file from disk.

### 4. Delete button on hover via `QListWidget` custom item widget

Each list row uses a `QWidget` containing the thumbnail `QLabel` and a hidden `QPushButton("×")`. The button is shown/hidden by installing an event filter on the row widget to catch `Enter`/`Leave` events.

**Alternative:** `QToolButton` inside a `QStyledItemDelegate` — more complex, harder to maintain.

### 5. Lookback indicator = coloured left border via stylesheet on item widget

Frames within the lookback window get a blue left border (`border-left: 3px solid #4A90D9`) applied to their row widget. A badge (`QLabel("LLM")`) is an alternative but adds clutter. The border is recomputed on every `frames_changed` signal.

## Risks / Trade-offs

- [Re-render on every frame change] → panel only renders when open; cost is negligible for ≤100 frames
- [Delete removes frame the user didn't intend] → no undo; mitigated by hover-only visibility (accidental clicks unlikely)
- [Lookback window shifts after delete] → this is correct and expected behaviour; the indicator reflects the new window immediately
