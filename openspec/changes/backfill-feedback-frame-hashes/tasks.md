## 1. Never match on unknown or empty hashes

- [x] 1.1 In `FeedbackStore.last_entry_for()` (`src/drawing_coach/feedback_store.py`), return `None` immediately when the requested `frame_hashes` is empty — with no frames captured there is nothing to de-duplicate against.
- [x] 1.2 In the same method, skip any candidate entry whose resolved hashes are empty, so an entry with unknown hashes can never match. Keep the newest-first walk and the existing mode filter.
- [x] 1.3 Add a short comment recording why empty means "unknown, never equal" rather than "matches another empty".

## 2. Derive missing hashes from the frame on disk

- [x] 2.1 Add a `FeedbackStore._derived_hashes: dict[str, list[str]]` instance cache, keyed by the entry's relative `frame_path`, initialised in `__init__`.
- [x] 2.2 Add `FeedbackStore._hashes_for(response) -> list[str]`: return `response.frame_hashes` unchanged when non-empty; otherwise resolve the frame via the existing `frame_path_for()`, decode it with `Image.open(path).copy()` — matching `CaptureEngine._load_frames_from_disk()`, **not** `overlay_image_for()`'s `.convert("RGB")` — and return `[hashlib.sha256(img.tobytes()).hexdigest()]`.
- [x] 2.3 Comment the decode line with a pointer to `CaptureEngine._load_frames_from_disk()`, since hash comparability depends on the two decoding identically.
- [x] 2.4 Return `[]` from `_hashes_for()` when there is no resolvable `frame_path`, and when decoding raises — log the decode failure at warning level via the module's `_log` and continue.
- [x] 2.5 Memoise both successes and failures in `_derived_hashes` so a missing or corrupt frame is not reopened on every captured frame; skip the cache entirely for entries that already carry recorded hashes.
- [x] 2.6 Route `last_entry_for()`'s comparison through `_hashes_for()`. Do not touch `load()` — derivation stays off the load path, and no derived value is written back to disk.

## 3. Tests — store (`tests/test_feedback_store.py`)

- [x] 3.1 Entry JSON with no `frame_hashes` but a `frame_path` pointing at a real frame PNG: `last_entry_for(mode, [<sha256 of that image>])` returns that entry.
- [x] 3.2 The derived hash equals the hash the live path produces for the same file — compute the expectation with `hashlib.sha256(Image.open(png).copy().tobytes()).hexdigest()`, mirroring `MainWindow._current_frame_hashes()`.
- [x] 3.3 Deriving hashes leaves the entry's JSON file byte-for-byte unchanged (read the file before and after).
- [x] 3.4 Entry with no `frame_hashes` and no `frame_path`: `last_entry_for(mode, [])` returns `None` — the regression test for the reported bug.
- [x] 3.5 Entry with no `frame_hashes` and a `frame_path` whose file was deleted: never matches, including against `[]`, and the entry still loads with its text/mode/timestamp intact.
- [x] 3.6 `frame_path` referencing an undecodable file (write junk bytes to a `.png`): `last_entry_for()` returns `None` rather than raising, and the remaining entries still load.
- [x] 3.7 `last_entry_for(mode, [])` returns `None` even when an entry with recorded non-empty hashes exists for that mode.
- [x] 3.8 An entry with recorded non-empty hashes still matches exactly as before, and no frame file is opened for it (assert via a monkeypatched `Image.open` or an absent `frame_path`).

## 4. Tests — panel (`tests/test_feedback_panel.py`)

- [x] 4.1 `update_request_state([])` leaves the Request Feedback button enabled and its tooltip empty, for a store whose history contains an entry with no `frame_hashes`.
- [x] 4.2 `update_request_state()` with hashes matching a backfilled entry disables the button and sets the "Already generated…" tooltip, proving derived entries de-duplicate like recorded ones.
- [x] 4.3 Confirm the existing enable/disable tests still pass unchanged.

## 5. Verify

- [x] 5.1 Run `xvfb-run -a uv run pytest tests/test_feedback_store.py tests/test_feedback_panel.py` and record the result. → 60 passed.
- [x] 5.2 Run the full suite (`xvfb-run -a uv run pytest`) to confirm nothing else depended on empty-hash entries matching. → 435 passed, 0 failed.
- [x] 5.3 Manually confirm against a real session directory containing a pre-`frame_hashes` entry: opening the app leaves Request Feedback enabled before the first capture, and it still disables immediately after feedback is generated.

### Verification results

Sections 5.1 / 5.2: `xvfb-run -a uv run pytest` — 435 passed, 0 failed. Targeted run of
`tests/test_feedback_store.py tests/test_feedback_panel.py` — 60 passed.

Section 5.3: driven against hand-built session directories on disk (`meta.json`,
`frames/`, `feedback/` laid out as `CaptureEngine`/`FeedbackStore` write them), resumed
through the real `CaptureEngine.load_session()` and rendered by a real `FeedbackPanel`
bound to a real `FeedbackStore`:

- Session A — entry with neither `frame_hashes` nor `frame_path`: buffer empty on resume,
  Request Feedback **enabled**, tooltip empty, history entry still loaded.
- Session B — entry with `frame_path` but no `frame_hashes`: frame reloaded from disk;
  button **enabled** before the first capture; hashing the resumed frame the way
  `MainWindow._current_frame_hashes()` does **disables** the button with the
  "Already generated for this drawing and mode" tooltip; a different hash re-enables it.

The same script run against the pre-fix `feedback_store.py` (commit `604a389`) fails 5 of
those 9 checks — reproducing the reported bug (button disabled with the misleading tooltip
before any capture) and confirming the checks are load-bearing rather than vacuous.

Not covered: the packaged GUI was not launched end-to-end. Driving it needs a real drawing
window to monitor and a configured LLM, neither available in this headless container; the
verification above exercises the real capture-resume, store, and panel objects instead.
