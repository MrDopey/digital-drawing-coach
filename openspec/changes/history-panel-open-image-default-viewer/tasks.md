## 1. History Panel — List Layout

- [x] 1.1 Switch `QListWidget` from `IconMode` to default `ListMode` (remove `setViewMode`, `setResizeMode`)
- [x] 1.2 Iterate `reversed(frames)` when populating the list so newest frames appear first
- [x] 1.3 Resize thumbnail icons to a compact size suitable for list rows (e.g. 48×48)

## 2. History Panel — Double-click to Open

- [x] 2.1 Store each `CapturedFrame` on its `QListWidgetItem` using `item.setData(Qt.ItemDataRole.UserRole, frame)`
- [x] 2.2 Connect `list_widget.itemDoubleClicked` signal to an `_open_frame` slot in `HistoryPanel`
- [x] 2.3 Implement `_open_frame(item)`: resolve the file path (use `frame.path` if set, otherwise save to a temp PNG via `tempfile.mkstemp(suffix=".png")`)
- [x] 2.4 Call `QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))` to open the resolved path
- [x] 2.5 Show a `QMessageBox.warning` if `openUrl` returns `False` (no default viewer registered)
- [x] 2.6 Add a hint label "Double-click a thumbnail to open it" below the list widget (visible only when frames are present)

## 3. Tests

- [x] 3.1 Add a pytest-qt test that constructs `HistoryPanel` with multiple frames and verifies the first list item has the latest timestamp
- [x] 3.2 Add a pytest-qt test that constructs `HistoryPanel` with a disk-backed `CapturedFrame` and verifies `QDesktopServices.openUrl` is called with the correct file URL on double-click (mock `QDesktopServices.openUrl`)
- [x] 3.3 Add a test for the in-memory path: `frame.path = None`, verify a temp file is created and `openUrl` is called with a `.png` path
- [x] 3.4 Add a test that `QMessageBox.warning` is shown when `openUrl` returns `False`

## 4. Documentation

- [x] 4.1 Update `README.md` to mention that history panel thumbnails can be double-clicked to open in the system image viewer
- [x] 4.2 Update `.claude/CLAUDE.md` if any architectural notes about the history panel need refreshing

## 5. Verification

- [x] 5.1 Run `uv run pytest` and confirm all tests pass
