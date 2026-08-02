## Why

The system tray icon's right-click menu has accumulated items that duplicate functionality already available from the main window, cluttering the one menu that's supposed to be a quick, at-a-glance control surface. It also has no way to bring the main window back once it's been closed to tray — the user has to know to double-click the icon (unwired) or quit and relaunch. The menu needs a cleanup pass: drop the redundant items and give the top item a real, expected job — reopening the main window.

## What Changes

- Remove **BREAKING** the following items from the tray icon's context menu: "Get Feedback", "Memory", and "Progress". These panels remain reachable from the main window's button row; only the tray-menu shortcuts to them go away.
- Replace the top item of the tray menu (previously "Get Feedback") with a "Show Drawing Coach" action that brings back the same main window shown at session start (`self.show()` / raise / activate on the existing `MainWindow` instance) — this is the primary gap being fixed, since closing the window to tray currently leaves no menu-driven way to reopen it.
- Reorder/regroup the remaining tray menu items (Show Drawing Coach, Pause/Resume Capture, Settings, About, Quit) with a separator so the restore action is visually distinct from the rest.
- Wire double-clicking the tray icon itself to the same restore behavior as the "Show Drawing Coach" menu item, so users don't have to open the menu at all to get the window back.

## Capabilities

### New Capabilities
- `system-tray-menu`: Defines the tray icon's context menu contents and the "restore main window" action.

### Modified Capabilities
(none — `memory-viewer` and `progress-panel` specs only require the panels be reachable "from the main window," which remains true via the existing button row; no requirement text changes)

## Impact

- Affected code: `src/drawing_coach/main_window.py` — `_build_tray()` (menu construction) and the new show/restore handler.
- No changes to `memory_viewer.py`, `progress_panel.py`, or the main window's button row; those panels stay reachable exactly as they are today, just no longer duplicated in the tray menu.
- No API, config, or dependency changes.
