## 1. MemoryStore: split formatting from the resummarize side effect

- [ ] 1.1 Extract the notes-formatting logic currently inline in `MemoryStore.summarise()` (session-count line, latest summary text, recent-observations-since-summary bullets) into a private helper, e.g. `_format_notes()`
- [ ] 1.2 Add a public `current_notes()` method that calls only `_format_notes()` — no `_try_resummarize()` call, no file writes
- [ ] 1.3 Update `summarise()` to: maybe call `_try_resummarize()` (unchanged threshold/config logic), then return `_format_notes()`
- [ ] 1.4 Verify `summarise()`'s existing behavior (cadence, cap, opt-out via `memory_resummarize_interval = 0`, graceful fallback on LLM failure) is unchanged after the refactor

## 2. Memory Viewer: use the read-only accessor

- [ ] 2.1 Change `MemoryViewerDialog._refresh()` (`memory_viewer.py`) to call `self._store.current_notes()` instead of `self._store.summarise()`
- [ ] 2.2 Confirm no other call site in the viewer (delete/clear-all/export) depends on `summarise()`'s side effects

## 3. Tests

- [ ] 3.1 Add/update a `MemoryStore` test asserting `current_notes()` never calls the re-summarisation LLM and never writes `memory_summaries.json`, even when the resummarize threshold has been crossed
- [ ] 3.2 Add/update a `MemoryStore` test asserting `current_notes()` and `summarise()` produce identical text when no new observations have been appended and no threshold is newly crossed
- [ ] 3.3 Add/update a Memory Viewer test (`tests/`) asserting that opening the viewer, and refreshing it after a delete or clear-all, does not modify `memory_summaries.json` and does not invoke the LLM
- [ ] 3.4 Search existing tests for any assertion that opening the Memory Viewer triggers re-summarisation, and correct it to reflect the new read-only behavior

## 4. Documentation

- [ ] 4.1 Update README.md (developer-facing) if it documents `MemoryStore.summarise()` usage, noting the new `current_notes()` read-only accessor and when to use each
- [ ] 4.2 Review `.claude/CLAUDE.md` for any memory-related guidance implied by this change (none expected — this is an internal refactor of `MemoryStore`, not a change to the app's memory data model or UI conventions) and update only if a genuine gap is found
- [ ] 4.3 Review `openspec/config.yaml` and propose changes only if this spec reveals a clear, recurring gap in the current rules (high threshold — likely no change needed for this narrow fix)

## 5. Verification

- [ ] 5.1 Run `uv run pytest` (via `xvfb-run -a uv run pytest` per project testing notes, since Memory Viewer tests import PyQt6/pynput) and confirm all tests pass
