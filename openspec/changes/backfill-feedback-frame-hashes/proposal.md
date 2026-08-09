## Why

The **Request Feedback** button is de-duplicated by comparing the current frame hashes and mode against saved feedback entries. Entries written before frame-hash tracking existed load with `frame_hashes = []`, and `MainWindow._current_frame_hashes()` also returns `[]` whenever the capture buffer is empty. The two empty lists compare equal, so opening a session that contains such an entry silently disables Request Feedback for the matching mode before a single frame has been captured — the user sees a disabled button and a tooltip claiming feedback was "already generated for this drawing", with no way to tell why.

Empty hashes are a *missing value*, not a real fingerprint, and the current code treats them as one.

## What Changes

- When loading feedback entries from disk, entries with no stored `frame_hashes` but a resolvable `frame_path` have their hashes derived from the frame image on disk, using the same SHA-256-over-`tobytes()` scheme the live capture path uses. Such entries then de-duplicate correctly instead of being dead weight.
- Entries whose hashes cannot be established — neither stored nor recoverable from disk — are treated as *unknown*, and SHALL never compare equal to a live hash list. In particular they no longer match an empty one.
- `FeedbackStore.last_entry_for()` stops matching on an empty live hash list: with no frames captured there is nothing to de-duplicate against, so Request Feedback stays enabled.

No user-facing configuration changes; no data migration is written back to disk (backfill is in-memory, per load).

## Capabilities

### New Capabilities
<!-- None — this corrects behaviour of existing capabilities. -->

### Modified Capabilities
- `feedback-deduplication`: the de-duplication match SHALL ignore entries with unknown frame hashes, and SHALL never suppress the button when the current frame set is empty.
- `feedback-persistence`: loading an entry that has no stored `frame_hashes` SHALL derive them from the entry's recorded `frame_path` when that file still exists.

## Impact

- `src/drawing_coach/feedback_store.py` — hash backfill during `load()`, and the match rule in `last_entry_for()`.
- `src/drawing_coach/feedback_panel.py` — `update_request_state()` behaviour follows from the store change; no signature change expected.
- `src/drawing_coach/main_window.py` — `_current_frame_hashes()` unchanged; its empty-list return is now handled by the store.
- Reads existing frame PNGs under `<session>/frames/` at load time (Pillow decode per un-hashed entry) — a cost only paid for entries that predate hash tracking.
- Tests: `tests/test_feedback_store.py`, `tests/test_feedback_panel.py`.
