> All tasks were implemented and verified before this change was written up —
> the defect was diagnosed and fixed live against the reporting user's machine,
> then recorded here. Commits: `cf03b6e` (hotkey listener + input probe) and
> `4a612a4` (hover routing).

## 1. Diagnose

- [x] 1.1 Add an application-wide input probe to `src/drawing_coach/perf.py`: a `QApplication`-level event filter counting every mouse event by type, the receiver types for moves, and a GUI-thread-sampled active-window/focus state, flushed as `PERF-INPUT` on the existing aggregation window.
- [x] 1.2 Confirm from the user's log that mouse moves reach the process in normal volume (~370 per 5 s) but are routed to `QLabel` and `_FrameRowWidget`, never the list viewport.
- [x] 1.3 Rule out the previously suspected causes with the same data: hover/paint cost (1.9 ms per 68 repaints), `itemAt()` hit-testing (0.02 ms/event), and pynput event taps (listen-only, keyboard-masked; user confirmed `"hotkey": ""` with no change).

## 2. Fix mouse-event routing

- [x] 2.1 Mark `_FrameRowWidget` and its thumbnail and timestamp `QLabel`s `WA_TransparentForMouseEvents` in `src/drawing_coach/history_panel.py`, leaving the delete button interactive.
- [x] 2.2 Move double-click handling from `_FrameRowWidget.mouseDoubleClickEvent` to `QListWidget.itemDoubleClicked`, resolving the frame from the item's `UserRole` data.
- [x] 2.3 Drop the now-unused `on_open` constructor parameter from `_FrameRowWidget`.

## 3. Fix the hotkey listener lifecycle

- [x] 3.1 Make `HotkeyManager._start()` stop any existing listener before creating a new one, so `set_hotkey()` + `start()` cannot orphan a pynput listener and its macOS event tap.

## 4. Tests

- [x] 4.1 Rewrite the three double-click tests to send events through the list viewport at the item's rect instead of directly to the row widget, using constructed events (`QTest`'s double-click is not delivered reliably under Xvfb).
- [x] 4.2 Add `test_row_and_labels_do_not_intercept_mouse_events`: the row and its labels are transparent, the delete button is not.
- [x] 4.3 Add `test_mouse_move_over_a_row_reaches_the_viewport_filter`: `viewport().childAt(centre)` returns nothing and a move at that point sets `_hovered_row`.
- [x] 4.4 Add hotkey listener tests: starting twice leaves exactly one listener with the first stopped; an empty hotkey stops any listener and creates none.
- [x] 4.5 Add input-probe tests: counts and move receivers are reported, the probe is a no-op when disabled, and an empty window emits nothing.

## 5. Verify

- [x] 5.1 `xvfb-run -a uv run pytest` green (417 tests); no new lint findings versus the pre-change baseline.
- [x] 5.2 Confirmed on the affected macOS machine by the reporting user: the history tab is responsive and hover highlights follow the cursor.
