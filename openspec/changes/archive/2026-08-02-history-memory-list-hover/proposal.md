## Why

The session history and memory viewer dialogs both present scrollable lists of items (captured frames, stored observations), but only the history panel currently highlights a row when the mouse moves over it (added in `session-history-redesign`). The memory viewer's observation tree has no such feedback, so users can't visually tell which row they're about to click/delete, making the two windows feel inconsistent.

## What Changes

- Add a background hover-highlight to each observation row in the Memory Viewer's tree, so moving the mouse over a row visually highlights it — matching the existing row-hover behavior in the Session History panel.
- Verify the Session History panel's existing row hover-highlight (from `session-history-redesign`) still behaves correctly; no behavioral change is expected there, but it's the reference behavior the memory viewer must match.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `memory-viewer`: adds a requirement that each observation row highlights its background on mouse hover, consistent with the history panel's row hover behavior.

## Impact

- `src/drawing_coach/memory_viewer.py` — `MemoryViewerDialog`'s `QTreeWidget` row rendering (`_refresh`) gains hover-highlight styling.
- No changes expected to `src/drawing_coach/history_panel.py` (already implements row hover-highlight) or `CaptureEngine`/`MemoryStore` data layers.
