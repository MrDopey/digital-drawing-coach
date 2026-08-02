## Context

`MainWindow._build_tray()` (`src/drawing_coach/main_window.py`) builds a single `QMenu` and attaches it to the `QSystemTrayIcon` via `setContextMenu()`. Today it has: Get Feedback, [separator], Pause/Resume Capture, Settings, Memory, Progress, [separator], About, Quit. `MainWindow.closeEvent()` already ignores the close and calls `self.hide()`, keeping the process alive in the tray — but nothing in the menu (or elsewhere) currently calls `self.show()` again, so once hidden the only way back is to quit and relaunch.

## Goals / Non-Goals

**Goals:**
- Trim the tray menu to remove the three duplicated shortcuts (Get Feedback, Memory, Progress) that are already available from the main window's button row.
- Give the menu a working "bring the window back" action as its first item, using the existing `MainWindow` instance (not a new window/dialog).

**Non-Goals:**
- Changing the main window's own button row (Get Feedback, History, Memory, Progress, Settings buttons stay as-is) — this change is scoped to the tray context menu only.
- Any change to `MemoryViewerDialog` or `ProgressPanel` themselves.

## Decisions

- **Reuse the existing `MainWindow` instance for restore, don't create a new one.** The proposal explicitly calls for "the same window as when the session starts" — that's the singleton `MainWindow` created at app launch, not a fresh window. The restore handler calls `self.show()`, `self.raise_()`, and `self.activateWindow()` on `self`.
- **Place the restore action as the first entry, replacing "Get Feedback."** Matches the request that "the top selection item" do this. The removed "Get Feedback" tray shortcut is still available from the main window's own button row once it's restored.
- **Keep the existing separator structure**, just shifted: `[Show Drawing Coach]`, separator, `[Pause/Resume Capture]`, `[Settings]`, separator, `[About]`, `[Quit]`. This preserves the existing visual grouping (primary action / session controls / info-and-exit) with one fewer item in the middle group.
- **No change to `memory-viewer` / `progress-panel` specs.** Both specs only require the panels be reachable "from the main window" (not specifically from the tray), which remains true via the unchanged button row.
- **Wire `QSystemTrayIcon.activated` to the same restore handler, filtered to `DoubleClick`.** The signal also fires with `Trigger` (single click, platform-dependent) and `MiddleClick`; only `DoubleClick` is handled so a stray single click doesn't unexpectedly pop the window in front of whatever the user is drawing in. This reuses `_restore_main_window()` from the menu item — no separate code path.

## Risks / Trade-offs

- [Users who relied on tray-menu shortcuts for Memory/Progress/Get Feedback lose one click of convenience] → Mitigation: those actions remain one click away on the main window's button row, which is shown immediately by the new top menu item.
- [Restoring a window that's already visible could be a no-op or steal focus unexpectedly] → Mitigation: `show()`/`raise_()`/`activateWindow()` are idempotent and safe to call on an already-visible window; this matches standard Qt tray-app restore patterns.
