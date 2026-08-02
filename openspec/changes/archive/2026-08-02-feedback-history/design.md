## Context

`FeedbackResponse` is a dataclass with `mode`, `text`, `timestamp`, `annotation_json`, `observations: list[dict]`, and `used_structured_output: bool` (the last two added by the structured-JSON-output-fallback change, already merged). `FeedbackEngine` keeps an in-memory `_history: list[FeedbackResponse]` that is lost on restart, and builds requests through two paths — `_call_structured` and `_call_prose` — both of which construct their own `FeedbackResponse`. Frame selection (single latest frame for `overlay` mode; latest + configured lookback window otherwise) happens inline inside `_build_messages`.

`FeedbackPanel` (`feedback_panel.py`) is already migrated onto `theme.py`/`design_system.py` (`Theme.overlay.apply_to(self)`, `PrimaryButton`, `MutedLabel`, `SectionHeader`) and already has: a title row, a mode row (horizontal `QRadioButton` strip + right-aligned **Request Feedback** `PrimaryButton` — this exact row is locked in by the merged `feedback-modes` spec), a loading label, a vertical `QSplitter` (top: zoom controls + a `_ZoomScrollArea`-wrapped image label showing the composited overlay image; bottom: a read-only `QTextEdit`), a Save Overlay row, and a Previous/Next history row. History today is in-memory only (`self._history`, `self._overlay_images: dict[int, PilImage.Image]`), lost on restart — that's the problem this change solves. None of the above is being rebuilt; the sidebar and thumbnail are layered on top of it.

`FeedbackPanel` is constructed in `MainWindow.__init__` (`self._feedback_panel = FeedbackPanel()`) *before* `self._capture.new_session()` / `self._capture.load_session()` run, so `CaptureEngine.session_dir` is `None` at panel-construction time. `MainWindow._switch_session()` and `_new_session()` currently only call into `self._capture`; neither touches `self._feedback_panel` at all.

The session directory structure already exists under `sessions_dir()/<session-id>/`; frames are stored as PNGs in `frames/`. `paths.py` follows the pattern `sessions_dir().parent / "..."` for cross-session data (e.g. the already-added `debug_log_dir()`), but per-session helpers should take the concrete `session_dir: Path` that callers (`CaptureEngine.session_dir`, `MainWindow`) already hold.

## Goals / Non-Goals

**Goals:**
- Persist every `FeedbackResponse` to disk with image hashes and, depending on mode, a thumbnail or a full composited image
- Load history for the active session on startup, and reload it whenever the active session changes
- Deduplicate: disable Request Feedback when same frames+mode already submitted
- Add a sidebar + mode-appropriate image preview to the existing panel layout without altering its current overlay-zoom/splitter/Prev-Next behavior

**Non-Goals:**
- Cross-session history browsing (only the active session's history is loaded at a time)
- Editing or deleting saved feedback entries
- Exporting feedback to PDF/text
- Reconciling `feedback-modes`' existing "Previous Feedback" scenario with the new sidebar (see proposal.md's "Known gap")

## Decisions

### 1. New `FeedbackStore` class owns disk persistence

`FeedbackStore(session_dir: Path)` handles save and load. `save()` writes `feedback/<session-id>/YYYYMMDD_HHMMSS_<mode>.json` containing every current `FeedbackResponse` field — `mode`, `text`, `timestamp`, `annotation_json`, `observations`, `used_structured_output`, `frame_hashes` — plus a `thumbnail_path`. `load()` reads all JSON files in the directory in filename order and reconstructs `FeedbackResponse` objects. This keeps I/O out of `FeedbackPanel` and `FeedbackEngine`.

**Alternative:** embed persistence in `FeedbackEngine` — rejected because the engine already has enough concerns (two request paths, structured-output fallback); separation makes testing easier.

### 2. `FeedbackResponse` gains `frame_hashes: list[str]` — computed locally, never round-tripped through the LLM

SHA-256 of each frame's PNG bytes (`CapturedFrame.image.tobytes()`), computed from the same frame selection `_build_messages` already performs (single latest frame for `overlay`; latest + lookback window otherwise). This is pure local computation on data already in memory before the request is dispatched — it is not sent to the LLM, is not part of `_STRUCTURED_RESPONSE_SCHEMA`, and the model is never asked to produce, echo, or acknowledge a hash. It is unrelated to the `observations` field the structured-output/prose paths already extract from the model's response (that's cross-session qualitative coaching memory, owned by `MemoryStore`; `frame_hashes` is same-session exact-image identity, owned by `FeedbackStore` — the two never overlap). To avoid duplicating frame-selection logic, extract it into a shared `_select_frames(frames, mode)` helper used by both `_build_messages` and the new hashing step; `request_feedback` computes hashes once before dispatching to `_call_structured`/`_call_prose`, and both pass `frame_hashes=` into the `FeedbackResponse` they construct. Deduplication checks `frame_hashes == last_entry.frame_hashes and mode == last_entry.mode` — only the last matching entry is compared, covering the common "Request Feedback clicked twice with no new capture" case.

**Alternative:** hash the image data every time Request Feedback is pressed — same cost, but cleaner to do it once at request time, and it already needs to happen once per request regardless of which of the two call paths is taken.

### 3. Two distinct image displays, chosen by mode — not one universal thumbnail

Overlay-mode entries keep the *existing* full-size zoomable/pannable annotated image in `_image_pane` — that widget and its zoom/pan/save behavior are unchanged. The non-overlay modes (Quick Hint, Full Critique, Practice Exercise), which today show no image at all, gain a new small (160×160 max) `QLabel` thumbnail of the last raw frame sent; clicking it opens the frame in the system default viewer via `QDesktopServices.openUrl`, mirroring `history_panel.py`'s `_open_frame`. `_render_current()` shows exactly one of {`_image_pane`, the new thumbnail label} per entry, based on whether that entry has a composited overlay image.

`FeedbackStore.save()` always writes the small raw-frame thumbnail (cheap, and keeps the on-disk format uniform across modes); when the response's mode is `overlay` and a composited image is supplied, it *additionally* writes the full-resolution PNG (`..._overlay.png`) so `FeedbackStore.load()` can repopulate `FeedbackPanel._overlay_images` on startup/session-switch — without this, reloaded overlay entries would only have a lossy small thumbnail and could no longer be zoomed or saved via the existing Save Overlay button, regressing the already-merged `overlay-feedback` spec for anything but the live, just-generated entry.

**Alternative:** persist only `annotation_json` and re-render the overlay on load — rejected; re-compositing requires the exact frame the annotations were drawn against, which would mean also persisting that raw frame at full resolution anyway, with no savings over just persisting the already-rendered composite.

### 4. Sidebar wraps the existing top row and vertical splitter; does not replace them

The existing top row (mode radio strip + right-aligned Request Feedback button) is left as-is beyond adding the disabled/tooltip behavior from Decision 6. A new left sidebar `QListWidget` (fixed ~180px width, reverse-chron entries) sits to the left of the *existing* vertical `QSplitter` (image pane/thumbnail + text edit), Save Overlay row, and Prev/Next row — all reparented into a right-hand container, with the sidebar and that container placed in an outer `QSplitter(Horizontal)` so the sidebar width is still user-adjustable, consistent with the app's existing divider pattern. The inner vertical splitter object is reused unmodified so the already-merged `overlay-feedback` spec's zoom/splitter-size/scroll-on-resize guarantees keep applying without re-verification of that logic.

Sidebar selection and Prev/Next stay in sync through the existing `_history_idx` + `_render_current()` machinery: the sidebar's `currentRowChanged` sets `_history_idx` and calls `_render_current()`; `_render_current()` also calls `setCurrentRow` on the sidebar (with signals blocked, to avoid re-entrant updates) so both controls always agree on the current entry.

**Alternative:** `QTableWidget` for the sidebar — heavier; a `QListWidget` is sufficient for single-column labelled rows, matching `history_panel.py`'s existing use of `QListWidget` for a similar list.

### 5. Generate button — no rename; disabled/tooltip logic added to the existing "Request Feedback" button

The button's label is "Request Feedback" (locked in by the merged `feedback-modes` spec and current code) — this change does not rename it. On any change to the current frame set or mode, `FeedbackPanel` recomputes whether the current frames+mode already match the last saved entry (via `FeedbackStore.last_entry_for`) and disables the button with tooltip "Already generated for this drawing and mode" if so. Since `FeedbackPanel` has no direct reference to `CaptureEngine`, `MainWindow` computes the current frame hashes (reusing the same `_select_frames`/hashing helper `FeedbackEngine` uses, not a duplicate implementation) and calls into the panel whenever `CaptureEngine.frames_changed` fires, the mode radio selection changes, or a request completes.

### 6. `FeedbackStore` must be (re)bound after construction, and again on every session change

Because `FeedbackPanel()` is built in `MainWindow.__init__` before `CaptureEngine.new_session()`/`load_session()` resolve `session_dir`, and because `_switch_session()`/`_new_session()` currently rebind nothing, `FeedbackPanel` gains a `set_store(store: FeedbackStore) -> None` method: it clears any previously-loaded sidebar entries and `_overlay_images`, calls `store.load()`, and repopulates the sidebar (selecting the most recent entry, satisfying `feedback-modes`' "opening the panel with prior history" scenario). `MainWindow` calls `feedback_panel.set_store(FeedbackStore(self._capture.session_dir))` once `session_dir` is resolved at startup, and again inside `_switch_session()` and `_new_session()` — otherwise the panel would keep showing the previous session's history after a switch, a gap the original version of this proposal missed entirely.

**Alternative:** reorder `MainWindow.__init__` so `new_session()`/`load_session()` runs before `FeedbackPanel()` is constructed — rejected; that ordering is already entangled with hotkey/tray/signal wiring that happens around it, and a small rebind method is a much more localized change than reordering constructor side effects.

### 7. New widgets must be design-system compliant

The sidebar rows and the new thumbnail label are built from `design_system.py` components (e.g. `MutedLabel` for row/thumbnail captions) and `theme.py` tokens — no raw `setStyleSheet()` calls or hex literals, since `tests/test_design_system_compliance.py` (merged since this proposal was first drafted) fails the build on exactly that. If a sidebar row ever needs both a hover highlight and a "currently selected" indicator simultaneously, follow the pattern `history_panel.py`'s `_FrameRowWidget` already establishes for combining a hover highlight with the lookback-window border: track each state as its own field and recompute one combined stylesheet from both, rather than two handlers each calling `setStyleSheet()` independently.

## Risks / Trade-offs

- [Thumbnail write adds latency to feedback save] → JPEG at 160×160 is < 20 ms; acceptable
- [Overlay PNG write adds additional latency/disk use for overlay-mode saves only] → composited images are already held in memory as a `PIL.Image` before this change; writing them out is a single additional `save()` call, not a new render
- [`frame_hashes` computed from PIL image bytes — not the PNG file] → consistent because frames are always saved from the same PIL Image; hash is stable for the same capture
- [History load on startup, and again on every session switch, adds I/O] → bounded by session entry count; typical sessions have < 50 entries
- [Nesting the existing vertical splitter inside a new outer horizontal splitter] → must confirm the overlay-feedback spec's "zoom resets on navigation" and "splitter preserves user-dragged sizes" scenarios still hold after reparenting; mitigated by reusing the same `QSplitter` instance and widgets rather than recreating them
