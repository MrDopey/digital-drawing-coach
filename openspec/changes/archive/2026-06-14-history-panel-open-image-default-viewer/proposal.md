## Why

Clicking images in the history panel currently does nothing useful. Users expect to be able to inspect a captured frame at full resolution using their preferred image viewer, but the panel provides no way to do this.

## What Changes

- Double-clicking a thumbnail in the history panel opens the corresponding image file in the system's default application for PNG files
- When a frame has no disk path (in-memory only), the image is saved to a temporary file and then opened
- A status hint ("Double-click to open") is shown so the affordance is discoverable

## Capabilities

### New Capabilities

- `history-panel-open-image`: Open a history panel thumbnail in the system's default image viewer on double-click, handling both disk-backed and in-memory frames

### Modified Capabilities

<!-- No existing spec-level requirements are changing -->

## Impact

- `src/drawing_coach/history_panel.py`: add double-click handler and open-file logic
- No new dependencies — uses `QDesktopServices.openUrl` (already available in PyQt6) with a `QUrl.fromLocalFile` path, which delegates to the OS default handler on all platforms
