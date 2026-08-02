# memory-viewer Specification

## Purpose
TBD - created by change long-term-memory. Update Purpose after archive.

## Requirements
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

### Requirement: Delete individual observations from memory viewer
Each observation row in the memory viewer SHALL have a delete button. Activating it SHALL remove that observation from the store immediately and refresh the viewer.

#### Scenario: User deletes an observation
- **WHEN** the user clicks the delete button on an observation row
- **THEN** the observation is removed from `memory.json` and disappears from the viewer

### Requirement: Clear all memory with confirmation
The memory viewer SHALL provide a "Clear All Memory" button. Activating it SHALL show a confirmation dialog before deleting all observations and summary history. On confirmation all observations and all summaries are removed from `memory.json` and `memory_summaries.json` respectively.

#### Scenario: User confirms clear all
- **WHEN** the user clicks Clear All Memory and confirms the dialog
- **THEN** all observations are removed from `memory.json`, all summaries are removed from `memory_summaries.json`, and the viewer shows the empty state

#### Scenario: User cancels clear all
- **WHEN** the user clicks Clear All Memory but cancels the confirmation dialog
- **THEN** neither file is modified and the viewer is unchanged

### Requirement: Export memory to user-chosen location
The memory viewer SHALL provide an "Export Memory" button that opens a destination-folder dialog and copies both `memory.json` and `memory_summaries.json` into the chosen folder.

#### Scenario: User exports memory
- **WHEN** the user clicks Export Memory and selects a destination folder
- **THEN** both `memory.json` and `memory_summaries.json` are copied into that folder and a success message is shown

#### Scenario: Exporting when summary history does not yet exist
- **WHEN** the user clicks Export Memory and `memory_summaries.json` does not yet exist (no re-summarisation has happened yet)
- **THEN** `memory.json` is still copied, `memory_summaries.json` is skipped, and the success message reflects what was actually exported
