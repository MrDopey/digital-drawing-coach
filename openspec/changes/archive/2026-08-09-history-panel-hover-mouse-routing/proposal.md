## Why

The Session History window's row hover-highlight took **several seconds** to respond on macOS. Four previous attempts (`a80c520` through `58e62f9`) tried to fix it inside the hover and paint code and all failed, because the premise was wrong: the hover code was never slow.

`HistoryPanel` tracks hover with an event filter installed on the `QListWidget` **viewport**. But `setItemWidget()` covers that viewport completely with real child widgets, and the row's `QLabel`s cover most of each row. Qt routes a mouse move to the topmost widget under the cursor, so every move was delivered to a `QLabel` or `_FrameRowWidget` and the viewport's filter never ran. The highlight only updated when the cursor happened to cross the few pixels of row margin where bare viewport is exposed.

Measured on the affected machine with the `perf-diagnostics` input probe: while the cursor was over the list, **~370 mouse moves arrived per 5-second window**, routed to `QLabel` and `_FrameRowWidget`, and **zero** reached the viewport. For comparison, the code all four previous attempts edited costs 1.9 ms per 68 repaints and 5.1 ms per 4 hit-tests.

The same investigation found that `HotkeyManager._start()` overwrote `self._listener` without stopping the previous listener, so `MainWindow`'s `set_hotkey()` + `start()` pair orphaned a pynput listener — and its macOS event tap and run-loop thread — for the life of the process, unreachable by `_stop()`. That violates the existing requirement that reconfiguring a hotkey unregisters the old one.

## What Changes

- `_FrameRowWidget` and its thumbnail and timestamp `QLabel`s are marked `WA_TransparentForMouseEvents`, so hit-testing falls through to the list viewport and the hover filter receives every move. The delete button is a child and is unaffected by the attribute, so it stays clickable.
- Double-click handling moves from `_FrameRowWidget.mouseDoubleClickEvent` to `QListWidget.itemDoubleClicked`, because a mouse-transparent row can no longer receive a double-click of its own. Observable behaviour is unchanged.
- `HotkeyManager._start()` now stops any existing listener before creating a new one, so exactly one listener (and one macOS event tap) exists at a time.
- `perf` gains an application-wide input probe: a `QApplication`-level event filter counting every mouse event the process receives, which receiver each move was routed to, and the active-window/focus state. This is the instrument that located the defect and is what distinguishes "events never arrive" from "events arrive but are not routed".
- The double-click tests previously sent events **directly to the row widget**, so they passed regardless of whether real hit-testing could reach it — the same false-green that let this regression ship. They now drive the list viewport, and two regression tests cover the routing itself.

## Capabilities

### New Capabilities
*(none — this is a defect resolution against existing capabilities)*

### Modified Capabilities
- `history-panel-theming`: adds a requirement that the hover highlight must actually receive mouse-move events when the cursor is over a row, constraining the row and its non-interactive children to be transparent to mouse events.
- `history-panel-open-image`: adds a requirement that double-click activation is independent of the row widget's own mouse handling.
- `stuck-detection`: adds a requirement that at most one global hotkey listener exists at a time, so repeated registration cannot orphan one.
- `perf-diagnostics`: adds the application-wide input probe requirement.

## Impact

- **Modified**: `src/drawing_coach/history_panel.py`, `src/drawing_coach/hotkey_manager.py`, `src/drawing_coach/perf.py`, `tests/test_history_panel.py`, `tests/test_perf_call_sites.py`, `tests/test_enhancements.py`.
- **Already landed**: commits `cf03b6e` (hotkey listener + input probe) and `4a612a4` (hover routing). Confirmed resolved by the reporting user — the history tab is responsive.
- **Dependencies**: none added.
- **Risk**: `WA_TransparentForMouseEvents` on the row means any future interactive child of `_FrameRowWidget` must be added as a child widget (children are unaffected by the attribute) rather than relying on the row's own mouse events.
- **Not addressed here** — two defects confirmed by the same investigation, both real and both distinct from this one: `frames_changed` receiver connections accumulate on every panel open (`receivers` observed climbing 2 → 3 → 4), and `_load_frames_from_disk` decodes every PNG on the GUI thread (a measured 677 ms startup stall that scales with frame count and capture resolution).
