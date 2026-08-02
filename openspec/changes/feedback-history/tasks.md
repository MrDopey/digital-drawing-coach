## 1. Data model — FeedbackResponse frame hashes

- [x] 1.1 Add `frame_hashes: list[str] = field(default_factory=list)` to the `FeedbackResponse` dataclass (alongside its existing `observations`/`used_structured_output` fields)
- [x] 1.2 Extract the mode-based frame-selection logic already inside `_build_messages` (single latest frame for `overlay`; latest + lookback window otherwise) into a shared `_select_frames(frames, mode)` helper. In `FeedbackEngine.request_feedback`, compute `hashlib.sha256(frame.image.tobytes()).hexdigest()` for each selected frame before dispatching, and pass `frame_hashes=` into the `FeedbackResponse` constructed by both `_call_structured` and `_call_prose`

## 2. FeedbackStore — disk persistence

- [x] 2.1 Create `src/drawing_coach/feedback_store.py` with class `FeedbackStore(session_dir: Path)`
- [x] 2.2 Implement `save(response: FeedbackResponse, last_frame: CapturedFrame | None, overlay_image: PIL.Image.Image | None = None)` — writes JSON to `feedback/<session-id>/YYYYMMDD_HHMMSS_<mode>.json` containing every `FeedbackResponse` field (`mode`, `text`, `timestamp`, `annotation_json`, `observations`, `used_structured_output`, `frame_hashes`); writes a 160×160 JPEG thumbnail of `last_frame` to `..._thumb.jpg`; when `overlay_image` is provided, additionally writes the full-resolution composited PNG to `..._overlay.png`
- [x] 2.3 Implement `load() -> list[FeedbackResponse]` — reads all JSON files in the feedback dir in filename order, reconstructs `FeedbackResponse` objects (skips malformed files with a warning log); also expose a way to fetch the loaded overlay image for an entry (e.g. `FeedbackStore.overlay_image_for(response) -> PIL.Image.Image | None`) by reading the matching `..._overlay.png` if present (also adds `thumbnail_path_for(response) -> Path | None`, needed by the panel to open the raw frame in the system viewer)
- [x] 2.4 Implement `last_entry_for(mode: str, frame_hashes: list[str]) -> FeedbackResponse | None` — returns the most recent entry whose mode and frame_hashes match, or None
- [x] 2.5 Add `feedback_dir(session_dir: Path) -> Path` helper to `paths.py`, returning `session_dir / "feedback"` (takes the concrete session directory, since callers — `CaptureEngine.session_dir`, `MainWindow` — already hold it, rather than re-deriving it from a bare session id)

## 3. FeedbackPanel / MainWindow — load history and (re)wire persistence

- [x] 3.1 Update `FeedbackPanel.__init__` to build the new sidebar and thumbnail widgets described in section 5, with no store required at construction time (the panel starts idle/empty — no session directory is resolved yet when `MainWindow.__init__` constructs it)
- [ ] 3.2 Add `FeedbackPanel.set_store(store: FeedbackStore) -> None`: clears any previously-loaded sidebar entries and `_overlay_images`, calls `store.load()`, and repopulates the sidebar and `_overlay_images` (via `store.overlay_image_for(...)` for overlay entries), selecting the most recent entry if any exist
- [ ] 3.3 In `show_feedback` (or wherever a new response is appended to `_history`), call `store.save(response, last_frame, overlay_image)` after appending, guarding for the case no store has been bound yet
- [ ] 3.4 In `MainWindow`, call `self._feedback_panel.set_store(FeedbackStore(self._capture.session_dir))` once the session directory is resolved at startup (after `new_session()`/`load_session()` runs), and again inside both `_switch_session()` and `_new_session()`, so the panel never keeps showing a previous session's history after a switch

## 4. Request Feedback button deduplication

- [ ] 4.1 Add a method on `FeedbackPanel` (e.g. `update_request_state(frame_hashes: list[str])`) that calls `store.last_entry_for(current_mode, frame_hashes)` and disables the existing "Request Feedback" button with tooltip "Already generated for this drawing and mode" if a match is found, re-enabling it otherwise
- [ ] 4.2 In `MainWindow`, compute the current frame hashes using the same `_select_frames`/hashing helper `FeedbackEngine` uses (not a duplicate implementation) and call `feedback_panel.update_request_state(...)` on: mode radio selection change, `CaptureEngine.frames_changed`, and after each successful generation

## 5. FeedbackPanel UI redesign

- [ ] 5.1 Wrap the existing top row (mode radio strip + Request Feedback button — unchanged beyond section 4's disabled-state wiring) and the existing vertical `QSplitter` (image pane/text edit), Save Overlay row, and Prev/Next row inside a new right-hand container; add a new left sidebar `QListWidget` (fixed ~180px width); place both in an outer `QSplitter(Horizontal)`
- [ ] 5.2 Populate the sidebar in reverse-chron order; each row labelled `DD Mon  HH:MM: <mode label>`; style rows via `design_system.py`/`theme.py` (no raw `setStyleSheet()`/hex literals); `currentRowChanged` sets `_history_idx` and calls `_render_current()`
- [ ] 5.3 Add a new thumbnail `QLabel` (~160×160, clickable — `mousePressEvent` calls `QDesktopServices.openUrl(QUrl.fromLocalFile(thumb_path))`), styled via `design_system.py`. `_render_current()` shows exactly one of {existing `_image_pane`, new thumbnail label} depending on whether the current entry has a composited overlay image
- [ ] 5.4 Extend `_render_current()` (not a new `_show_entry` — it already plays that role) so it also calls `setCurrentRow` on the sidebar with signals blocked, keeping sidebar selection, Prev/Next, and the displayed entry always in sync
- [ ] 5.5 After a new generation: insert the entry at the top of the sidebar, select it, and let the existing `show_feedback` → `_render_current()` flow display it

## 6. Tests

- [ ] 6.1 Unit tests for `FeedbackStore.save`/`load` round-trip: all `FeedbackResponse` fields preserved (`mode`, `text`, `timestamp`, `annotation_json`, `observations`, `used_structured_output`, `frame_hashes`), thumbnail always written, overlay PNG written only when `overlay_image` is supplied
- [ ] 6.2 Unit test for `FeedbackStore.last_entry_for` — match found, no match, empty history
- [ ] 6.3 Unit test for `FeedbackEngine` — `FeedbackResponse.frame_hashes` populated with correct SHA-256 values, covering both the structured (`_call_structured`) and prose (`_call_prose`) paths, and both overlay (single-frame) and lookback-window (multi-frame) selection
- [ ] 6.4 pytest-qt test: Request Feedback button disabled when hashes+mode match; re-enabled on mode change
- [ ] 6.5 pytest-qt test: clicking a sidebar row navigates to that entry and stays in sync with Previous/Next; new sidebar rows and the thumbnail label are design-system components (extending the existing `test_feedback_panel.py` pattern of asserting `isinstance(..., PrimaryButton/MutedLabel)`)
- [ ] 6.6 pytest-qt test: `FeedbackPanel.set_store()` loads an existing session's history into the sidebar and clears a previously-bound session's entries when called again

## 7. Documentation

- [ ] 7.1 Update `README.md` with feedback persistence and deduplication behaviour
- [ ] 7.2 Review `.claude/CLAUDE.md` — no new UI conventions beyond existing guidelines (design-system compliance is already documented there); no changes needed
- [ ] 7.3 Review `openspec/config.yaml` — no recurring gap identified; no changes needed
- [ ] 7.4 Run `uv run pytest` and confirm all tests pass
