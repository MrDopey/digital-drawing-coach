## Why

In the Feedback Management panel, Overlay entries get a full-resolution, zoomable, pannable image pane while every other mode (Quick Hint, Full Critique, Practice Exercise) gets a 160×160 thumbnail that cannot be enlarged, zoomed, or inspected. Users cannot actually see what the coach was looking at for three of the four feedback modes — and the thumbnail's "Click to open full image" caption is a lie, because the only file on disk for those entries *is* the 160px JPEG.

The full-resolution frame already exists on disk (`<session>/frames/HHMMSS_NNNN.png`) and is already handed to the persistence layer, so the fix costs no extra storage — the reference is simply discarded today.

## What Changes

- Feedback entries record the path of the full-resolution source frame in their JSON. No new image bytes are written — the frame file already exists on disk.
- The Feedback Management panel renders **every** entry's image through the same zoomable/pannable image pane that Overlay entries use today. Zoom controls (−/Reset/+ and `Ctrl+Wheel`) work for all modes, not just Overlay.
- The separate fixed-size thumbnail pane is **removed from the codebase**, not retained as a fallback. The panel has exactly one image display path.
- The 160×160 `_thumb.jpg` is no longer written at all, and `thumbnail_path` is dropped from the entry JSON. Nothing else in the codebase reads either — the history panel's own 48px frame thumbnails are a separate mechanism and are untouched.
- The misleading "Click to open full image" caption is resolved by deletion: the caption, and the click-to-open-in-system-viewer behaviour it described, go away with the pane.
- **Accepted consequence:** an entry with no resolvable full-resolution frame — saved before this change, or whose frame file has since been removed — now shows **no image at all**; the image section collapses and the feedback text fills the panel.
- **Not in scope:** no migration or backfill for existing entries, and no cleanup of `_thumb.jpg` files already on disk. Old entry JSONs keep an ignored `thumbnail_path` key.

## Capabilities

### New Capabilities

None — this change modifies existing behaviour.

### Modified Capabilities

- `feedback-persistence`: the saved entry JSON gains a reference to the full-resolution source frame used for that feedback and loses the `thumbnail_path` field; the 160×160 thumbnail is no longer written. Loading an entry SHALL resolve the recorded frame when it still exists on disk.
- `feedback-panel-redesign`: the main content area SHALL show a full-size zoomable image for all feedback modes; the small thumbnail preview and its click-to-open-in-system-viewer behaviour are removed outright, with no fallback.
- `overlay-feedback`: the full-detail scrolling and zoom requirements, currently scoped to the overlay image, SHALL apply to whichever image the panel is displaying.

## Impact

- `src/drawing_coach/feedback_store.py` — write the source frame path into the entry JSON and expose a lookup for it; delete `_THUMBNAIL_SIZE`, the thumbnail-writing code, the `thumbnail_path` JSON field, and `thumbnail_path_for()`.
- `src/drawing_coach/feedback_engine.py` — `FeedbackResponse` needs to carry the source frame path so it survives the save/load round-trip.
- `src/drawing_coach/feedback_panel.py` — reduce to one zoomable image pane fed by either an overlay image or a full-resolution frame; delete `_ClickableThumbnail`, `_thumb_pane`, `_thumb_label`, `_thumb_caption`, `_thumb_paths`, `_show_thumbnail`, and `THUMBNAIL_SIZE`.
- Read-only dependency on `capture_engine.CapturedFrame.path` (already populated) and the `<session>/frames/` layout.
- Tests: `tests/test_feedback_store.py` (existing `thumbnail_path_for` tests are deleted) and the feedback panel tests.
- No config, API, or dependency changes. Entries written by older builds still load without error — their `thumbnail_path` is ignored and their missing `frame_path` resolves to nothing.
