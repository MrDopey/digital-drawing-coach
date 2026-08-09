## 1. Never match on unknown or empty hashes

- [ ] 1.1 In `FeedbackStore.last_entry_for()` (`src/drawing_coach/feedback_store.py`), return `None` immediately when the requested `frame_hashes` is empty — with no frames captured there is nothing to de-duplicate against.
- [ ] 1.2 In the same method, skip any candidate entry whose resolved hashes are empty, so an entry with unknown hashes can never match. Keep the newest-first walk and the existing mode filter.
- [ ] 1.3 Add a short comment recording why empty means "unknown, never equal" rather than "matches another empty".

## 2. Derive missing hashes from the frame on disk

- [ ] 2.1 Add a `FeedbackStore._derived_hashes: dict[str, list[str]]` instance cache, keyed by the entry's relative `frame_path`, initialised in `__init__`.
- [ ] 2.2 Add `FeedbackStore._hashes_for(response) -> list[str]`: return `response.frame_hashes` unchanged when non-empty; otherwise resolve the frame via the existing `frame_path_for()`, decode it with `Image.open(path).copy()` — matching `CaptureEngine._load_frames_from_disk()`, **not** `overlay_image_for()`'s `.convert("RGB")` — and return `[hashlib.sha256(img.tobytes()).hexdigest()]`.
- [ ] 2.3 Comment the decode line with a pointer to `CaptureEngine._load_frames_from_disk()`, since hash comparability depends on the two decoding identically.
- [ ] 2.4 Return `[]` from `_hashes_for()` when there is no resolvable `frame_path`, and when decoding raises — log the decode failure at warning level via the module's `_log` and continue.
- [ ] 2.5 Memoise both successes and failures in `_derived_hashes` so a missing or corrupt frame is not reopened on every captured frame; skip the cache entirely for entries that already carry recorded hashes.
- [ ] 2.6 Route `last_entry_for()`'s comparison through `_hashes_for()`. Do not touch `load()` — derivation stays off the load path, and no derived value is written back to disk.

## 3. Tests — store (`tests/test_feedback_store.py`)

- [ ] 3.1 Entry JSON with no `frame_hashes` but a `frame_path` pointing at a real frame PNG: `last_entry_for(mode, [<sha256 of that image>])` returns that entry.
- [ ] 3.2 The derived hash equals the hash the live path produces for the same file — compute the expectation with `hashlib.sha256(Image.open(png).copy().tobytes()).hexdigest()`, mirroring `MainWindow._current_frame_hashes()`.
- [ ] 3.3 Deriving hashes leaves the entry's JSON file byte-for-byte unchanged (read the file before and after).
- [ ] 3.4 Entry with no `frame_hashes` and no `frame_path`: `last_entry_for(mode, [])` returns `None` — the regression test for the reported bug.
- [ ] 3.5 Entry with no `frame_hashes` and a `frame_path` whose file was deleted: never matches, including against `[]`, and the entry still loads with its text/mode/timestamp intact.
- [ ] 3.6 `frame_path` referencing an undecodable file (write junk bytes to a `.png`): `last_entry_for()` returns `None` rather than raising, and the remaining entries still load.
- [ ] 3.7 `last_entry_for(mode, [])` returns `None` even when an entry with recorded non-empty hashes exists for that mode.
- [ ] 3.8 An entry with recorded non-empty hashes still matches exactly as before, and no frame file is opened for it (assert via a monkeypatched `Image.open` or an absent `frame_path`).

## 4. Tests — panel (`tests/test_feedback_panel.py`)

- [ ] 4.1 `update_request_state([])` leaves the Request Feedback button enabled and its tooltip empty, for a store whose history contains an entry with no `frame_hashes`.
- [ ] 4.2 `update_request_state()` with hashes matching a backfilled entry disables the button and sets the "Already generated…" tooltip, proving derived entries de-duplicate like recorded ones.
- [ ] 4.3 Confirm the existing enable/disable tests still pass unchanged.

## 5. Verify

- [ ] 5.1 Run `xvfb-run -a uv run pytest tests/test_feedback_store.py tests/test_feedback_panel.py` and record the result.
- [ ] 5.2 Run the full suite (`xvfb-run -a uv run pytest`) to confirm nothing else depended on empty-hash entries matching.
- [ ] 5.3 Manually confirm against a real session directory containing a pre-`frame_hashes` entry: opening the app leaves Request Feedback enabled before the first capture, and it still disables immediately after feedback is generated.
