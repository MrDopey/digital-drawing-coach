## Why

Opening the Memory Viewer to look at your coach's notes calls `MemoryStore.summarise()` — the same method used to build the live LLM prompt context. If the re-summarisation threshold has been crossed, that call silently fires a real LLM request and appends a new entry to `memory_summaries.json`. A window billed as a read-only viewer should never make a network call or mutate persisted state just from being opened.

## What Changes

- Add a non-mutating accessor on `MemoryStore` that formats the coach's notes block purely from already-persisted state (last saved summary + raw observations since it, or all raw observations if no summary exists yet) — no re-summarisation check, no LLM call, no file writes.
- `MemoryViewerDialog` uses this new accessor instead of `summarise()` when populating the "Current coach's notes" text area, on both initial load and every `_refresh()` (e.g. after a delete or clear-all).
- No behavior change to the actual feedback-request path: `main_window.py`'s call to `MemoryStore.summarise()` before an LLM feedback request keeps triggering re-summarisation exactly as today.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `memory-viewer`: the coach's-notes preview must be populated from a read-only fetch of persisted state, never triggering re-summarisation or a network call.
- `memory-store`: add a non-mutating notes-preview accessor, distinct from `summarise()`, that never triggers condensation or writes `memory_summaries.json`.

## Impact

- `src/drawing_coach/memory_store.py` — new read-only method (e.g. `current_notes()`), sharing formatting logic with `summarise()` but skipping `_try_resummarize()`.
- `src/drawing_coach/memory_viewer.py` — `_refresh()` calls the new accessor instead of `summarise()`.
- No change to `main_window.py`, `feedback_engine.py`, or the `memory-context` capability (LLM prompt injection and its re-summarisation cadence are unaffected).
