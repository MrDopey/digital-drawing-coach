## Context

`MemoryStore.summarise(max_obs=20)` does two things at once: (1) it may trigger `_try_resummarize()`, a live LLM call that condenses raw observations into a new summary and appends it to `memory_summaries.json`, and (2) it formats and returns the coach's-notes text. `main_window.py` calls it right before an LLM feedback request — that's the intended trigger point (see `memory-context` capability). `memory_viewer.py`'s `_refresh()` also calls it, purely to display a preview, with no awareness that it can side-effect a network call and a file write.

## Goals / Non-Goals

**Goals:**
- The Memory Viewer's "Current coach's notes" preview reflects persisted state only — no LLM call, no file mutation — whether opened once or repeatedly (e.g. after each delete).
- Preserve the exact re-summarisation behavior and cadence for the real feedback-request path (`main_window.py` → `summarise()`).
- Keep the formatting (session count line, summary text, recent-observations bullets) identical between the live prompt and the viewer preview, so the viewer stays a truthful preview rather than a differently-worded approximation.

**Non-Goals:**
- Not changing `memory_resummarize_interval` semantics, caps, or the `memory-context`/`memory-store` re-summarisation requirements.
- Not adding a manual "refresh notes now" trigger to the viewer — out of scope for this change.

## Decisions

- **Split formatting from the resummarize check.** Extract the existing formatting logic in `summarise()` (session count line + latest summary + recent observations since it) into a private helper, e.g. `_format_notes()`. `summarise()` becomes: maybe call `_try_resummarize()`, then return `_format_notes()`. A new public method `current_notes()` calls only `_format_notes()` — no resummarize check, no mutation.
  - Alternative considered: have the viewer call `summarise()` but pass a flag like `allow_resummarize=False`. Rejected — a boolean flag on the existing mutating method is easy to get backwards at a call site and doesn't read as "this is safe," whereas a separate read-only-named method is self-documenting and impossible to misuse.
- **Viewer switches to `current_notes()`.** `memory_viewer.py:71` changes from `self._store.summarise()` to `self._store.current_notes()`. No other behavior in the viewer changes (delete/clear-all/export are unaffected — they were never gated on `summarise()`).
- **No change to `main_window.py`.** It keeps calling `summarise()` immediately before building the feedback request, which is the one place resummarization should legitimately fire.

## Risks / Trade-offs

- [Risk] Divergence: someone edits formatting in one of `summarise()`/`current_notes()` later and forgets the other → viewer preview silently stops matching what's actually sent to the LLM. → Mitigation: shared `_format_notes()` helper means there's only one place formatting logic lives; both public methods are thin wrappers around it.
- [Risk] A test may currently assert the viewer's notes call also drives resummarization (asserting on `memory_summaries.json` after opening the viewer). → Mitigation: check `tests/` for viewer tests during implementation and update any such assertion to reflect the new, correct read-only behavior.
