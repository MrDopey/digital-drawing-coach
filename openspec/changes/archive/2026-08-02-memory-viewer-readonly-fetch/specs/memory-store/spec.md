## ADDED Requirements

### Requirement: Non-mutating coach's-notes preview, separate from summarise()
`MemoryStore` SHALL expose a read-only accessor (e.g. `current_notes()`) that formats the coach's-notes block — the session-count line, the most recent persisted summary (if any), and raw observations appended since it (or all raw observations if no summary exists yet) — using exactly the same formatting as `summarise()`, but without ever checking the re-summarisation threshold, calling the re-summarisation LLM, or writing to `memory_summaries.json`. Callers that only need to preview or display current notes (e.g. the Memory Viewer) SHALL use this accessor instead of `summarise()`.

#### Scenario: Preview reflects persisted state with no side effects
- **WHEN** `current_notes()` is called, regardless of how many observations have been appended since the last re-summarisation
- **THEN** it returns the formatted coach's-notes text built from already-persisted observations and summaries, and makes no LLM call and no write to any file

#### Scenario: Preview matches what summarise() would format from the same persisted state
- **WHEN** `current_notes()` and `summarise()` are called back-to-back with no new observations appended in between and no re-summarisation threshold newly crossed
- **THEN** both return identical text, since both build from the same persisted summary and raw-observations state using shared formatting logic

#### Scenario: Empty store
- **WHEN** `current_notes()` is called and there are no observations and no summaries
- **THEN** it returns an empty string, matching `summarise()`'s behavior for an empty store
