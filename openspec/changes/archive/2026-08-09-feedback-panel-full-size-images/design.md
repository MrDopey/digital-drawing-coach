## Context

The Feedback Management panel (`FeedbackPanel`, `src/drawing_coach/feedback_panel.py`) has two mutually-exclusive image display paths, selected in `_render_current` (`feedback_panel.py:450-460`):

- `_image_pane` — a `QLabel` inside a `_ZoomScrollArea`, no size cap, driven by `_render_overlay_image` (`feedback_panel.py:506-520`). Only overlay entries reach it.
- `_thumb_pane` — a `_ClickableThumbnail` with `setFixedSize(160, 160)` (`feedback_panel.py:239`), driven by `_show_thumbnail` (`feedback_panel.py:490-504`). Everything else reaches it.

The panel-side cap is only half the problem. `FeedbackStore.save()` (`feedback_store.py:28-56`) writes the screenshot as a 160×160 JPEG and keeps nothing else, while the overlay is saved at full PNG resolution. So the small image is small on disk too — removing `setFixedSize` alone would only produce a blurry upscale.

The full-resolution frame does exist: `CaptureEngine._store_frame` writes `<session>/frames/HHMMSS_NNNN.png` (`capture_engine.py:350-352`), and `CapturedFrame` carries `.path`. `FeedbackStore.save()` already receives that `CapturedFrame` as `last_frame` and discards everything but the pixels it downsamples.

Constraints: sessions can be pruned wholesale (`capture_engine._cleanup_old_sessions`), and entries written by older builds have no frame reference at all — both cases must degrade rather than error.

## Goals / Non-Goals

**Goals:**
- Every feedback entry displays its image in the existing full-size, scrollable, zoomable pane, regardless of mode.
- Zoom controls (−/Reset/+ and `Ctrl+Wheel`) apply to whatever image is displayed.
- No new image bytes written to disk — reference the frame that already exists, and stop writing the thumbnail that is now unread.
- Exactly one image display path in the panel; the fixed-size thumbnail pane is deleted, not retained as a fallback.
- Entries with no resolvable full-resolution image collapse the image section without error.

**Non-Goals:**
- No migration or backfill of entries saved before this change, and no cleanup of `_thumb.jpg` files already on disk.
- No change to overlay compositing, to the "Save Overlay" action, or to the history panel's own 48px thumbnails (`history_panel.py`).
- No change to what is sent to the LLM.
- No replacement for click-to-open-in-system-viewer; it is removed along with the thumbnail it acted on.
- No small per-entry previews in the sidebar, now or later — it stays a plain text list. This is the decided position, not a deferral, and it is why no downscaled image needs to be stored anywhere.

## Decisions

### 1. Carry the frame reference on `FeedbackResponse`, not by naming convention

Today's sidecar files are found by naming convention: `overlay_image_for` (and `thumbnail_path_for`, which this change deletes) derive their paths from the entry's `_stem`, so nothing has to round-trip through the dataclass. The source frame is different — it lives in another directory under a name the feedback entry does not control, so it cannot be derived and must be persisted and read back.

**Decision:** add `frame_path: str | None = None` to the `FeedbackResponse` dataclass (`feedback_engine.py:196-203`), persist it as `frame_path` in the entry JSON, and populate it in `load()`.

*Alternative rejected:* a separate `FeedbackStore.frame_path_for(response)` that re-reads the JSON. That means a second read of a file `load()` already parsed, and leaves the value invisible to any other consumer of `FeedbackResponse`. `frame_hashes` is already a capture-layer concern living on this dataclass, so the field is consistent with what is there.

### 2. Store the path relative to the session directory

`feedback_dir(session_dir)` is `session_dir / "feedback"` (`paths.py:37-38`), so `FeedbackStore` can recover the session root as `self._dir.parent` without a constructor change.

**Decision:** persist `frame_path` relative to the session directory (e.g. `frames/094132_0007.png`) and resolve it against `self._dir.parent` on load, guarded by `.is_file()`.

*Alternative rejected:* an absolute path. Session directories live under the XDG data home, which differs across machines and changes if the user relocates their data; absolute paths would break silently on any move. Relative paths also keep the JSON readable and test fixtures portable.

### 3. One image pane, one source-selection step — the thumbnail pane is deleted

**Decision:** `_render_current` resolves a single "image to show" for the entry, in priority order:

1. the composited overlay image (`self._overlay_images[idx]`, eagerly loaded today),
2. otherwise the full-resolution frame at the entry's resolved `frame_path`,
3. otherwise nothing — the image section collapses and the feedback text fills the panel.

Both image cases render through `_image_pane`. `_thumb_pane`, `_thumb_label`, `_thumb_caption`, `_thumb_paths`, `_show_thumbnail`, the `_ClickableThumbnail` class, and the `THUMBNAIL_SIZE` constant are removed from `feedback_panel.py`. The "Save Overlay" button stays bound to case 1 — the overlay-feedback spec's saveability requirement is unchanged, and offering "Save Overlay" for a plain screenshot would be wrong.

*Alternative rejected:* keeping the thumbnail as a fallback for entries whose frame cannot be resolved. It preserves an image for legacy entries, but at the cost of a second display path, a second widget tree, and a second set of states to keep consistent — permanently, to serve entries that age out of relevance as sessions are pruned. A collapsed image section is an honest representation of "there is no image for this entry"; a 160px stand-in that cannot be zoomed is the confusing behaviour this change exists to remove.

### 4. Stop writing the thumbnail entirely

With the pane gone, nothing reads `_thumb.jpg`. `thumbnail_path_for` has exactly one caller (`feedback_panel.py:334, 367`), and `history_panel.py` builds its own 48px thumbnails from frames through an unrelated path.

**Decision:** delete `_THUMBNAIL_SIZE`, the thumbnail-writing block, the `thumbnail_path` JSON field, and `thumbnail_path_for()` from `feedback_store.py`, along with the two `thumbnail_path_for` tests in `tests/test_feedback_store.py`. Saving a feedback entry no longer performs a PIL resize or a JPEG encode.

*Alternative rejected:* keeping the writer against possible future use — e.g. sidebar row previews. Writing a file nothing reads is a cost paid on every feedback response for a feature that does not exist; if the sidebar ever wants previews, it can generate them from the recorded `frame_path` at that point.

Old entry JSONs keep their now-unused `thumbnail_path` key and their `_thumb.jpg` files on disk. `load()` ignores unknown keys, so they are inert; no cleanup pass is worth the risk of deleting user data.

### 5. Cache the source `QPixmap` per entry; render scales from the cache

`_render_overlay_image` currently calls `_pil_to_pixmap(overlay_img)` on **every** zoom step — a full PIL→bytes→`QImage`→`QPixmap` conversion per keystroke or wheel notch. Extending that to full-resolution frames (which can be 4K screenshots) would also mean re-decoding a PNG from disk on every zoom step.

**Decision:** convert once per entry into `self._current_pixmap` when `_render_current` selects the image, and have the render/zoom step scale from that cached pixmap. Full-resolution frames are opened lazily at display time, not eagerly for the whole session in `set_store`.

*Alternative rejected:* eagerly loading every entry's frame in `set_store` alongside the overlay images. A long session's worth of decoded full-resolution screenshots held in memory at once is not acceptable, and most are never viewed.

### 6. Requirement names in the `overlay-feedback` delta stay as-is

The two generalised requirements are still titled "Overlay image is viewable at full detail via scrolling" and "Overlay image is zoomable", though their bodies now cover any displayed feedback image. Renaming would require `RENAMED` plus `MODIFIED` deltas on the same requirements; the normative text is what matters and the titles can be tidied in a later cleanup.

## Risks / Trade-offs

- **Pre-existing entries lose their image entirely.** Entries saved before this change have no `frame_path`, and with the thumbnail pane gone they now render with a collapsed image section — a visible regression for anyone with history. → Accepted and explicit: the user chose end-to-end removal over a permanent second display path. The feedback text, which is the substance of the entry, is unaffected and gains the space.
- **Full-resolution frames are large; decoding one on entry selection could feel sluggish.** → Decode once per entry and cache (Decision 5); navigation already re-renders, and a single PNG decode is well under the panel's existing per-entry work. Revisit with a downscale-on-load cap only if measurably slow.
- **A referenced frame can disappear** (session pruning, manual cleanup) leaving a dangling path. → `.is_file()` guard on resolve, collapsing the image section; covered by an explicit spec scenario.
- **Adding a field to `FeedbackResponse` touches a dataclass used across the engine, store, and panel.** → The field is optional with a `None` default, so every existing construction site keeps working and old JSON loads unchanged.
- **Removing `thumbnail_path_for` is a public-surface deletion on `FeedbackStore`.** → Its only caller is the panel code being rewritten in the same change; a repo-wide grep confirms no other consumer. The two tests covering it are deleted alongside.
- **The change is only visible for newly-generated feedback**, so a user testing against an existing session may see no difference — or, now, may see images vanish. → Call this out in the verification steps; generate a fresh entry to confirm.
- **Non-overlay entries now occupy the splitter's top section**, changing the panel's default proportions for three modes. → Reuse the existing overlay split sizing so all modes look consistent rather than inventing a third layout.

## Open Questions

None. The one question raised during design — whether the sidebar should eventually show small per-entry previews — was answered **no**, and is recorded as a non-goal above. The sidebar stays a plain text list.
