## 1. CaptureEngine — buffer mutation API

- [x] 1.1 Add `frames_changed = pyqtSignal()` to `CaptureEngine`; emit after every `_buffer` append and after `remove_frame`
- [x] 1.2 Implement `remove_frame(frame: CapturedFrame)` — rebuild `_buffer` deque excluding the target frame (by identity); emit `frames_changed`

## 2. HistoryPanel — live updates & delete buttons

- [x] 2.1 Refactor `HistoryPanel` to accept a live `CaptureEngine` reference instead of a snapshot list; connect to `frames_changed` signal to re-render
- [x] 2.2 Replace `QListWidget` rows with custom item widgets (`QWidget` containing thumbnail `QLabel` + hidden `QPushButton("×")`)
- [x] 2.3 Install event filter on each item widget to show the delete button on `Enter` and hide on `Leave`
- [x] 2.4 Connect delete button `clicked` to `CaptureEngine.remove_frame(frame)` for the corresponding frame

## 3. HistoryPanel — lookback indicator

- [x] 3.1 Add `_update_lookback_indicator()` method: determines the lookback window (`frames[-(lookback+1):]`) using `config.lookback_frames` and applies a blue left border stylesheet to those item widgets; clears the border on all others
- [x] 3.2 Call `_update_lookback_indicator()` on initial render and on every `frames_changed` signal

## 4. MainWindow wiring

- [x] 4.1 Update `MainWindow` to pass `CaptureEngine` (not a snapshot list) when opening `HistoryPanel`
- [x] 4.2 Verify the history panel opens correctly from the menu/toolbar action

## 5. Tests

- [x] 5.1 Unit test `CaptureEngine.remove_frame`: frame removed from buffer, file not deleted, `frames_changed` emitted
- [x] 5.2 Unit test `CaptureEngine.remove_frame` with unknown frame: no error, buffer unchanged
- [x] 5.3 pytest-qt test: delete button visible on hover, hidden otherwise; clicking it removes the row from the panel

## 6. Documentation

- [x] 6.1 Update `README.md` to mention per-frame deletion and the lookback indicator in the history panel
- [x] 6.2 Review `.claude/CLAUDE.md` — no new UI conventions beyond existing guidelines; no changes needed
- [x] 6.3 Review `openspec/config.yaml` — no recurring gap identified; no changes needed
- [x] 6.4 Run `uv run pytest` and confirm all tests pass (3 pre-existing failures in test_diagnostics.py / test_stuck_detector.py confirmed present on main, unrelated to this change; all history-frame-management tests pass)
