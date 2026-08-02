## MODIFIED Requirements

### Requirement: Memory viewer shows all observations grouped by category
The system SHALL provide a memory viewer dialog accessible from the main window (e.g. via a Settings or Tools menu). The viewer SHALL list all stored observations in reverse-chronological order, grouped by category. Each observation row SHALL show its date and note text. The viewer SHALL also display the current coach's notes summary (read-only text area) at the top, populated via a non-mutating fetch of already-persisted state — opening the viewer, or refreshing it after a delete or clear-all, SHALL NOT trigger an LLM re-summarisation call or write to `memory_summaries.json`.

#### Scenario: Memory viewer opened with observations
- **WHEN** the user opens the memory viewer and observations exist
- **THEN** observations are displayed grouped by category in reverse-chronological order

#### Scenario: Memory viewer opened with no observations
- **WHEN** the user opens the memory viewer and no observations exist
- **THEN** the viewer shows an empty state message (e.g. "No observations recorded yet")

#### Scenario: Opening the viewer never triggers re-summarisation
- **WHEN** the user opens the memory viewer and the re-summarisation threshold (`memory_resummarize_interval`) has already been crossed
- **THEN** the coach's-notes preview is still populated from the last persisted summary and raw observations since it, no LLM call is made, and `memory_summaries.json` is not modified

#### Scenario: Repeated refresh stays read-only
- **WHEN** the viewer's `_refresh()` runs again after the user deletes an observation or clears all memory
- **THEN** the coach's-notes preview is re-populated from persisted state only, with no LLM call and no write to `memory_summaries.json`
