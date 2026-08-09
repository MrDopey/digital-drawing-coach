## 1. Persist the full-resolution frame reference

- [x] 1.1 Add `frame_path: str | None = None` to the `FeedbackResponse` dataclass in `src/drawing_coach/feedback_engine.py` (after `frame_hashes`), keeping the default so every existing construction site is unaffected
- [x] 1.2 In `FeedbackStore.save()` (`src/drawing_coach/feedback_store.py`), derive the session-relative path of `last_frame.path` (relative to `self._dir.parent`) and write it into the entry JSON as `frame_path`; write `null` when `last_frame` is `None` or has no `path`
- [x] 1.3 In `FeedbackStore.load()`, read `frame_path` from the JSON (defaulting to `None` for entries written before this change) onto the reconstructed `FeedbackResponse`
- [x] 1.4 Add `FeedbackStore.frame_path_for(response) -> Path | None` that resolves `response.frame_path` against `self._dir.parent` and returns it only when `.is_file()`

## 2. Remove thumbnail generation from the store

- [ ] 2.1 Delete the `_THUMBNAIL_SIZE` constant and the thumbnail-writing block from `FeedbackStore.save()` — saving an entry no longer performs a PIL resize or JPEG encode
- [ ] 2.2 Remove the `thumbnail_path` key from the entry JSON written by `save()`
- [ ] 2.3 Delete the `thumbnail_path_for()` method; confirm with a repo-wide grep that its only callers are the panel call sites rewritten in group 4
- [ ] 2.4 Confirm `load()` tolerates the now-obsolete `thumbnail_path` key present in entries written by older builds (unknown keys are ignored, not passed to the dataclass)

## 3. Test the persistence layer

- [ ] 3.1 In `tests/test_feedback_store.py`, delete `test_thumbnail_path_for_returns_none_when_absent` and `test_thumbnail_path_for_returns_path_when_present`
- [ ] 3.2 Update any remaining store tests that assert on `thumbnail_path` in the JSON or on a `_thumb.jpg` file existing
- [ ] 3.3 Add a test that saving with a `CapturedFrame` whose `path` is under `<session>/frames/` records a session-relative `frame_path` and writes **no** image file other than the overlay PNG for overlay entries
- [ ] 3.4 Add a test that saving with `last_frame=None` records `frame_path` as `null` and completes without error
- [ ] 3.5 Add a test that `load()` round-trips `frame_path`, that an entry JSON with no `frame_path` key loads with `frame_path is None`, and that a legacy JSON carrying `thumbnail_path` loads without error
- [ ] 3.6 Add tests that `frame_path_for` returns the resolved path when the frame file exists and `None` when the entry has no `frame_path` or the referenced file has been deleted

## 4. Reduce the panel to one image display path

- [ ] 4.1 In `src/drawing_coach/feedback_panel.py`, delete the `_ClickableThumbnail` class, the `THUMBNAIL_SIZE` constant, and the `_thumb_pane` / `_thumb_label` / `_thumb_caption` widget construction (including the caption "Click to open full image") and their splitter registration
- [ ] 4.2 Delete `self._thumb_paths`, `_show_thumbnail()`, and every remaining reference to the thumbnail pane in `show_feedback()`, `set_store()`, `show_error()`, and `_clear_display()`; drop any now-unused imports (e.g. `QDesktopServices`, `QUrl`) if nothing else uses them
- [ ] 4.3 Replace the per-zoom pixmap conversion with a per-entry cache: add `self._current_pixmap: QPixmap | None`, and rename `_render_overlay_image` to a source-agnostic `_render_image` that scales from that cached pixmap by `self._zoom_factor` instead of re-converting the PIL image on every zoom step
- [ ] 4.4 Add `self._frame_paths: dict[int, Path]`, populated from `store.frame_path_for(response)` in both `set_store()` and `show_feedback()` — paths only, no eager image decoding
- [ ] 4.5 Rework `_render_current()` to select one image source — overlay image, else the entry's full-resolution frame (opened lazily here and converted into `self._current_pixmap`) — showing `_image_pane` for both and hiding it entirely when neither resolves, so the feedback text fills the panel
- [ ] 4.6 Keep the "Save Overlay" button bound to the overlay case only, and keep the existing splitter sizing so overlay and non-overlay entries lay out consistently
- [ ] 4.7 Ensure `_set_zoom` drives the shared `_render_image` so zoom controls and `Ctrl+Wheel` work for full-resolution frames as well as overlays, and that zoom still resets to 1.0 on navigation
- [ ] 4.8 Confirm `_clear_display()` and `show_error()` hide the image pane and reset `self._current_pixmap`, so no stale image survives navigation to an entry with no image

## 5. Test the panel

- [ ] 5.1 In `tests/test_feedback_panel.py`, delete or rewrite any test covering the thumbnail pane, its click-to-open behaviour, or `THUMBNAIL_SIZE`
- [ ] 5.2 Add a test that a non-overlay entry with a resolvable full-resolution frame shows `_image_pane` and that the displayed pixmap matches the frame's full resolution rather than 160px
- [ ] 5.3 Add a test that an overlay entry still shows `_image_pane` with its composited image and that "Save Overlay" is visible only for that case
- [ ] 5.4 Add a test that an entry with no `frame_path` (or a dangling one) hides the image pane entirely without error, leaving the feedback text visible
- [ ] 5.5 Add a test that zooming while a non-overlay frame is displayed changes the rendered pixmap size, and that navigating to another entry resets the zoom to 100%

## 6. Verify

- [ ] 6.1 Grep the repo for `thumbnail_path`, `THUMBNAIL_SIZE`, `_thumb`, and `_ClickableThumbnail` to confirm no stragglers remain in `feedback_panel.py` / `feedback_store.py`, and that `history_panel.py`'s own 48px thumbnails are untouched
- [ ] 6.2 Run the full suite with `xvfb-run -a uv run pytest` and confirm no regressions, including `tests/test_design_system_compliance.py`
- [ ] 6.3 Launch the app, generate a fresh Quick Hint (or Full Critique) entry, and confirm the panel shows the full-resolution frame large, scrollable, and zoomable via the buttons and `Ctrl+Wheel`
- [ ] 6.4 Confirm an Overlay entry is unchanged in behaviour, and that an entry from a pre-change session now shows no image with the feedback text filling the panel — the accepted consequence, not a crash
- [ ] 6.5 Confirm a newly-saved entry's `feedback/` directory contains only the JSON and, for overlay entries, `_overlay.png` — no `_thumb.jpg`
