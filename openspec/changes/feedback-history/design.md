## Context

`FeedbackResponse` is a dataclass with `mode`, `text`, `timestamp`, `annotation_json`. `FeedbackEngine` keeps an in-memory `_history: list[FeedbackResponse]` that is lost on restart. `FeedbackPanel` is a `QWidget` with a mode combo, generate button, feedback text area, and prev/next navigation — no sidebar, no thumbnail, no persistence. The session directory structure already exists under `sessions/<session-id>/`; frames are stored as PNGs in `frames/`.

## Goals / Non-Goals

**Goals:**
- Persist every `FeedbackResponse` to disk with image hashes and a thumbnail
- Load history for the active session on startup
- Deduplicate: disable Generate when same frames+mode already submitted
- Redesign popup with sidebar + thumbnail + top controls

**Non-Goals:**
- Cross-session history browsing (only the active session's history is loaded)
- Editing or deleting saved feedback entries
- Exporting feedback to PDF/text

## Decisions

### 1. New `FeedbackStore` class owns disk persistence

`FeedbackStore(session_dir: Path)` handles save and load. Save writes `feedback/<session-id>/YYYYMMDD_HHMMSS_<mode>.json` containing the response fields as JSON plus a `thumbnail_path` pointing to a small PNG saved alongside. Load reads all JSON files in the directory in filename order and reconstructs `FeedbackResponse` objects. This keeps I/O out of `FeedbackPanel` and `FeedbackEngine`.

**Alternative:** embed persistence in `FeedbackEngine` — rejected because the engine already has enough concerns; separation makes testing easier.

### 2. `FeedbackResponse` gains `frame_hashes: list[str]`

SHA-256 of each frame's PNG bytes (computed from `CapturedFrame.image` at request time). Stored in the JSON file. Deduplication checks whether `frame_hashes == last_entry.frame_hashes and mode == last_entry.mode`. Only the last matching entry is compared (not the full history) — this covers the common case of "generate clicked twice without a new capture".

**Alternative:** hash the image data every time Generate is pressed — same cost, but cleaner to do it once at request time.

### 3. Thumbnail = 160×120 JPEG saved next to the JSON

`FeedbackStore.save()` scales and saves the last frame's `PIL.Image` as `<stem>_thumb.jpg`. `FeedbackPanel` loads it with `QPixmap`. Small enough to keep I/O fast; JPEG chosen for size.

### 4. FeedbackPanel redesign uses `QSplitter`

Left pane: `QListWidget` (sidebar, fixed ~180px width) listing entries in reverse-chron. Right pane: `QVBoxLayout` with thumbnail `QLabel` (clickable via `mousePressEvent`) + scrollable `QTextEdit` for feedback text. Top bar (above splitter): mode combo + Generate button. Prev/Next buttons below the text area.

**Alternative:** `QTableWidget` for sidebar — heavier; `QListWidget` is sufficient for single-column labelled rows.

### 5. Generate button disabled state

On any change to the current frame set or mode, `FeedbackPanel._update_generate_state()` is called. It computes hashes of current buffer frames and compares to `_store.last_entry_for(mode, hashes)`. If a match exists, the button is disabled with a tooltip "Already generated for this drawing and mode". A new capture (buffer changes) or mode switch re-enables it.

## Risks / Trade-offs

- [Thumbnail write adds latency to feedback save] → JPEG at 160×120 is < 20 ms; acceptable
- [frame_hashes computed from PIL image bytes — not the PNG file] → consistent because frames are always saved from the same PIL Image; hash is stable for the same capture
- [History load on startup adds I/O] → bounded by session entry count; typical sessions have < 50 entries
