## 1. Data model — FeedbackResponse frame hashes

- [ ] 1.1 Add `frame_hashes: list[str] = field(default_factory=list)` to the `FeedbackResponse` dataclass
- [ ] 1.2 In `FeedbackEngine.request_feedback`, compute `hashlib.sha256(frame.image.tobytes()).hexdigest()` for each selected frame and attach to the response

## 2. FeedbackStore — disk persistence

- [ ] 2.1 Create `src/drawing_coach/feedback_store.py` with class `FeedbackStore(session_dir: Path)`
- [ ] 2.2 Implement `save(response: FeedbackResponse, last_frame: CapturedFrame | None)` — writes JSON to `feedback/<session-id>/YYYYMMDD_HHMMSS_<mode>.json` and thumbnail to `..._thumb.jpg` (160×120 JPEG)
- [ ] 2.3 Implement `load() -> list[FeedbackResponse]` — reads all JSON files in the feedback dir in filename order, reconstructs `FeedbackResponse` objects (skips malformed files with a warning log)
- [ ] 2.4 Implement `last_entry_for(mode: str, frame_hashes: list[str]) -> FeedbackResponse | None` — returns the most recent entry whose mode and frame_hashes match, or None
- [ ] 2.5 Add `feedback_dir(session_id: str) -> Path` helper to `paths.py`

## 3. FeedbackPanel — load history and wire persistence

- [ ] 3.1 Update `FeedbackPanel.__init__` to accept an optional `FeedbackStore` and load existing history via `store.load()` on init
- [ ] 3.2 In `add_response`, call `store.save(response, last_frame)` after appending to in-memory history
- [ ] 3.3 Wire `FeedbackStore` construction in `MainWindow` using the active session directory; pass to `FeedbackPanel`

## 4. Generate button deduplication

- [ ] 4.1 Add `_update_generate_state()` to `FeedbackPanel` — computes current frame hashes, calls `store.last_entry_for(mode, hashes)`, disables button with tooltip if match found
- [ ] 4.2 Call `_update_generate_state()` on: mode combo change, every new capture arriving (connect to `CaptureEngine.frames_changed` or equivalent), and after each successful generation

## 5. FeedbackPanel UI redesign

- [ ] 5.1 Refactor layout: add top control row with mode combo + Generate button; wrap remaining content in `QSplitter(Horizontal)`
- [ ] 5.2 Left pane: `QListWidget` sidebar (fixed width ~180px) populated in reverse-chron order; each item labelled `DD Mon  HH:MM: <mode label>`; `currentRowChanged` signal jumps to that entry
- [ ] 5.3 Right pane: thumbnail `QLabel` (clickable — `mousePressEvent` calls `QDesktopServices.openUrl(QUrl.fromLocalFile(thumb_path))`); `QTextEdit` (read-only) for feedback text; Prev/Next buttons below
- [ ] 5.4 `_show_entry(idx)` method that updates both the right pane and the sidebar selection atomically
- [ ] 5.5 After new generation: insert entry at top of sidebar, select it, and show in right pane

## 6. Tests

- [ ] 6.1 Unit tests for `FeedbackStore.save` and `load` round-trip (fields preserved, thumbnail written)
- [ ] 6.2 Unit test for `FeedbackStore.last_entry_for` — match found, no match, empty history
- [ ] 6.3 Unit test for `FeedbackEngine` — `FeedbackResponse.frame_hashes` populated with correct SHA-256 values
- [ ] 6.4 pytest-qt test: Generate button disabled when hashes+mode match; re-enabled on mode change

## 7. Documentation

- [ ] 7.1 Update `README.md` with feedback persistence and deduplication behaviour
- [ ] 7.2 Review `.claude/CLAUDE.md` — no new UI conventions beyond existing guidelines; no changes needed
- [ ] 7.3 Review `openspec/config.yaml` — no recurring gap identified; no changes needed
- [ ] 7.4 Run `uv run pytest` and confirm all tests pass
