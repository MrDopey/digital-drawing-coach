## Context

De-duplication of the **Request Feedback** button runs through one comparison in `FeedbackStore.last_entry_for()`:

```python
if response.mode == mode and response.frame_hashes == frame_hashes:
```

Both sides can be empty for reasons that have nothing to do with the images matching:

- `load()` fills `frame_hashes=data.get("frame_hashes", [])`, so entries written before hash tracking existed (`frame_hashes` landed with the `feedback-history` change; `frame_path` only much later, with `feedback-panel-full-size-images`) load as `[]`.
- `MainWindow._current_frame_hashes()` returns `[]` when the capture buffer is empty.

`[] == []` is therefore read as "same drawing, same mode", and the button is disabled with a tooltip the user cannot act on.

Two properties of the surrounding code shape the fix:

- **`last_entry_for()` re-reads the whole session from disk on every call**, and it is called from `MainWindow._update_request_dedup_state()`, which is wired to `CaptureEngine.frames_changed` — i.e. on every captured frame. Any per-entry image decoding added here is on a hot path.
- **The live hash is computed over a disk-decoded image whenever a session is resumed.** `CaptureEngine._load_frames_from_disk()` rebuilds the buffer with `Image.open(png).copy()`, and `_current_frame_hashes()` hashes those objects. So a hash derived from a frame PNG is directly comparable to the live hash, provided both decode the file the same way.

## Goals / Non-Goals

**Goals:**

- An entry with no stored `frame_hashes` but an intact `frame_path` participates in de-duplication, using hashes derived from its frame image on disk.
- An entry whose hashes cannot be established never suppresses the button.
- An empty current frame set never suppresses the button.
- No added disk decoding on the common path, where every entry already carries recorded hashes.

**Non-Goals:**

- Rewriting entry JSON on disk to persist the derived hashes. A migration-on-load would mutate the user's session data as a side effect of opening a panel, and the derivation is cheap enough to redo.
- Recovering hashes for entries that have no `frame_path` at all (see Decisions — this is the majority of genuinely legacy entries, and there is no sound way to do it).
- Changing the hash scheme, the capture dedup threshold, or when `_update_request_dedup_state()` fires.

## Decisions

### Represent "unknown hashes" as the empty list, and fix the match rule instead of the type

`FeedbackResponse.frame_hashes` stays `list[str]` with its `default_factory=list`. Rather than introduce `list[str] | None` — which would ripple through `feedback_engine.py`, `feedback_store.save()`, and every construction site in the tests for no user-visible gain — the empty list keeps its natural meaning of *"no fingerprint available"*, and `last_entry_for()` stops treating it as a comparable value:

```python
def last_entry_for(self, mode, frame_hashes):
    if not frame_hashes:
        return None                     # nothing to de-duplicate against
    for response in reversed(self.load()):
        if response.mode != mode:
            continue
        hashes = self._hashes_for(response)
        if hashes and hashes == frame_hashes:
            return response
    return None
```

The two `if not …` guards are what actually fix the reported bug; the backfill in `_hashes_for()` is what makes recoverable entries useful again.

*Alternative considered:* a sentinel `None`. Rejected — it makes every read site handle two empty-ish states, and the JSON already round-trips a missing field to `[]`.

### Derive lazily in `last_entry_for()`, not eagerly in `load()`

`load()` is called on every dedup evaluation (once per captured frame), and also by `FeedbackPanel.set_store()`. Decoding every un-hashed entry's PNG inside `load()` would put a Pillow decode per legacy entry on the capture path.

Instead, derivation happens only for the entries `last_entry_for()` actually inspects — those matching the requested mode, walking newest-first — and results are memoised on the store instance, keyed by the entry's relative `frame_path`:

```python
self._derived_hashes: dict[str, list[str]] = {}
```

The cache lives as long as the `FeedbackStore`, which is replaced wholesale on session switch (`FeedbackPanel.set_store()`), so it cannot leak across sessions. Entries that fail derivation are cached as a failure too, so a missing or corrupt frame is not re-opened on every frame captured.

*Alternative considered:* eager backfill inside `load()`, which reads more simply. Rejected on the hot-path cost above.

*Alternative considered:* caching on `FeedbackResponse` by mutating `frame_hashes` in place. Rejected — `load()` builds fresh objects each call, so the mutation would be thrown away every time.

### Decode the frame exactly as `CaptureEngine._load_frames_from_disk()` does

Derivation uses `Image.open(path).copy()` and then `hashlib.sha256(img.tobytes()).hexdigest()` — no `.convert("RGB")`. `tobytes()` is mode- and size-dependent, so the derived hash is only comparable to the live one if both sides decode identically; the live side is `_load_frames_from_disk()`. (`FeedbackStore.overlay_image_for()` does convert to RGB, but that is for display, and must not be copied here.)

This couples the store to the capture engine's decode convention. The coupling is recorded as a comment at the derivation site pointing at `_load_frames_from_disk()`, rather than by extracting a shared helper — one call site each, and a shared helper would invite the wrong one (`overlay_image_for`) to adopt it.

### `frame_hashes` is derived only from `frame_path`, and most legacy entries have neither

Worth stating plainly, because it bounds what this change can fix: `frame_hashes` was introduced with `feedback-history`, and `frame_path` only with `feedback-panel-full-size-images`. Entries old enough to lack `frame_hashes` therefore also lack `frame_path`, and hold no reference to any image on disk. For those, the backfill can do nothing and the never-match guard is the whole fix.

The backfill covers the narrower case where a `frame_path` exists but hashes do not — entries written by a build between the two, and any future entry saved with a frame but an empty hash list.

*Alternative considered:* matching a legacy entry to a frame in `<session>/frames/` by comparing the entry's timestamp to the frames' filename timestamps. Rejected — it is a guess, and a wrong guess is worse than no hash: it would fabricate a fingerprint that silently disables the button against an image the user never submitted. Session pruning and the capture dedup threshold both make "nearest frame in time" unreliable.

## Risks / Trade-offs

- **Derived hash does not match the live hash** because the captured in-memory image and the re-decoded PNG differ in mode or bit depth → the entry simply fails to de-duplicate, which is the safe direction (button stays enabled). This is the same round-trip the live buffer already relies on after a session resume, so a mismatch would be a pre-existing bug in dedup, not one this change introduces.
- **Decode cost on a session with many un-hashed entries** → bounded by the memoisation and by only inspecting entries of the requested mode; a failure is cached as a failure, so pathological sessions decode each frame at most once per store instance.
- **Cache staleness if a frame file is deleted mid-session** (frame deletion, session pruning) → a cached hash could outlive its file. Consequence is limited to one stale dedup comparison; the store is rebuilt on session switch. Not worth invalidation machinery, but noted.
- **Empty-frame-set guard slightly widens when the button is enabled** → with no frames captured, pressing Request Feedback sends a request with no images. That path already exists (`MainWindow._request_feedback()` handles `frames == []` with `latest_image = None`) and is unchanged here; the button being enabled with nothing to send is pre-existing behaviour, not a regression introduced by this change.

## Migration Plan

None. The change is read-path only: no schema change, no file writes, no config. Existing entry JSON is untouched, so rollback is reverting the code.

## Open Questions

- Should Request Feedback be disabled outright when the capture buffer is empty (nothing to send), rather than merely not-deduplicated? That is a separate behaviour question from this bug and is deliberately left alone here.
