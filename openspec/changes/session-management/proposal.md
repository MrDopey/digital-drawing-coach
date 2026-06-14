## Why

Users have no way to manage, name, or switch between drawing sessions — every launch either creates a new session or implicitly continues the last one, making it impossible to revisit past work or organise sessions by subject or date.

## What Changes

- New session picker dialog shown on app launch, listing all saved sessions with name, date/time, and a thumbnail (last captured frame)
- Thumbnail expands to a larger preview on hover
- Options: Resume, New Session, Delete (picker is skipped when no sessions exist)
- Sessions gain a user-editable name stored in `meta.json`; default is generated from the timestamp (e.g. `Session 14 Jun 2026, 09:41`)
- Name is editable inline in the picker (double-click or pencil icon) and from inside the main window
- Sessions menu / button in the main window for in-app switching or creating a new session
- Switching saves the current session state and loads the selected one
- Active session name shown in the main window title bar (e.g. `Drawing Coach — Session 14 Jun 2026, 09:41`)
- `meta.json` gains a `name` field; thumbnail reuses the most recently written frame PNG from `frames/` — no separate thumbnail file needed

## Capabilities

### New Capabilities
- `session-picker`: Launch-time dialog listing all sessions with name, date, thumbnail; supports Resume / New / Delete actions
- `session-naming`: User-editable session name stored in `meta.json`, with inline editing in picker and main window
- `session-switching`: In-app Sessions menu for switching between sessions or creating a new one without restarting

### Modified Capabilities
- `screenshot-capture`: Session storage must write / update `meta.json` with a `name` field on session create and rename

## Impact

- `src/drawing_coach/` — new `session_picker_dialog.py`; changes to `main_window.py` (title bar, Sessions menu), `session_manager.py` (name read/write, thumbnail resolution)
- `meta.json` schema gains optional `name: str` field
- No new dependencies; thumbnail reuses existing frame PNGs
