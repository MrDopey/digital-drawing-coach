# memory-store Specification

## Purpose
TBD - created by change long-term-memory. Update Purpose after archive.

## Requirements
### Requirement: Persist drawing observations to memory.json
The system SHALL maintain a `memory.json` file in the app data directory that persists across sessions. The file SHALL store a list of observations, each containing `date` (ISO-8601), `session_id` (string), `category` (string, e.g. `anatomy`, `perspective`, `line_quality`), and `note` (short string). The total number of stored observations SHALL be capped at a configurable maximum (`memory_max_observations`, default 200); when the cap is reached the oldest observations SHALL be pruned before appending new ones.

#### Scenario: First observation written to new file
- **WHEN** an observation is appended and `memory.json` does not yet exist
- **THEN** the file is created and contains the new observation

#### Scenario: Observation appended to existing file
- **WHEN** an observation is appended and `memory.json` already has entries
- **THEN** the new observation is added and the file is saved

#### Scenario: Cap exceeded — oldest pruned
- **WHEN** appending an observation would bring the total above the configured `memory_max_observations` (default 200)
- **THEN** the oldest observation(s) are removed before the new one is appended so the total stays at the configured cap

#### Scenario: Memory loaded on startup
- **WHEN** the application starts and `memory.json` exists
- **THEN** all stored observations are loaded into `MemoryStore` and available for the coach's-notes prompt context and the UI

### Requirement: Extract observations from LLM response text
The system SHALL support two ways of recording observations from a feedback response, matching whichever path `FeedbackEngine` used for that request:
- **Structured path (primary)**: when the feedback response was obtained via structured JSON output, the system SHALL accept the already-parsed `{category, note}` observation records directly (no text parsing involved) and append them to the store with the current date and session ID.
- **Prose path (fallback)**: when the feedback response was obtained via the prose fallback, the system SHALL attempt to parse a `<!-- observations: [...] -->` HTML comment from the response text containing a JSON array of `{category, note}` objects, exactly as before. Successfully parsed observations SHALL be appended to the store with the current date and session ID. If the comment is absent or malformed, no observations are recorded and no error is shown to the user.

#### Scenario: Structured observations appended directly
- **WHEN** a feedback response was produced via the structured-output path and includes an `observations` array
- **THEN** each `{category, note}` entry is appended to the store with the current date and session ID, with no text parsing performed

#### Scenario: Structured observations array is empty
- **WHEN** a feedback response was produced via the structured-output path and its `observations` array is empty
- **THEN** no observations are appended and no error is shown to the user

#### Scenario: Valid observations comment present (prose fallback path)
- **WHEN** an LLM response was produced via the prose fallback path and includes a well-formed `<!-- observations: [...] -->` comment
- **THEN** the observations are parsed, appended to the store, and the comment is stripped from the displayed feedback text

#### Scenario: Observations comment absent (prose fallback path)
- **WHEN** an LLM response was produced via the prose fallback path and contains no `<!-- observations: -->` comment
- **THEN** no observations are recorded and the response text is displayed as-is

#### Scenario: Malformed observations comment (prose fallback path)
- **WHEN** an LLM response was produced via the prose fallback path and contains a `<!-- observations: -->` comment with invalid JSON
- **THEN** no observations are recorded, a debug log entry is written, and the comment is stripped from the displayed text

### Requirement: Coach's notes are periodically re-summarised by default (every 20 observations), with opt-out
`MemoryStore` SHALL track how many observations have been appended since the last re-summarisation. By default (`memory_resummarize_interval = 20`), once at least that many observations have been appended since the last re-summarisation, the next call to `summarise()` SHALL trigger a single LLM call that condenses the accumulated raw notes into a shorter block. Between condensation passes, `summarise()` SHALL format the coach's notes block directly from raw observations, with no LLM call. Setting `memory_resummarize_interval` to `0` SHALL disable condensation entirely, keeping notes raw forever.

#### Scenario: Raw notes between condensation passes
- **WHEN** fewer observations have been appended since the last re-summarisation than `memory_resummarize_interval`
- **THEN** `summarise()` formats the coach's notes block from raw observations without making an LLM call

#### Scenario: Threshold reached triggers condensation
- **WHEN** `memory_resummarize_interval` is `N > 0` (default `20`) and `N` observations have been appended since the last re-summarisation
- **THEN** the next `summarise()` call triggers one LLM call that condenses the raw notes into a shorter block

#### Scenario: User disables condensation
- **WHEN** `memory_resummarize_interval` is set to `0`
- **THEN** `summarise()` always formats the coach's notes block from raw observations and never makes an LLM call

#### Scenario: Condensation failure falls back gracefully
- **WHEN** the re-summarisation LLM call fails or times out
- **THEN** `summarise()` returns the previous (raw or last-condensed) notes unchanged and logs a debug entry

### Requirement: Persist a separately-capped summary history in its own file; only the most recent summary feeds the LLM
The system SHALL maintain a `memory_summaries.json` file, separate from `memory.json`, in the same app data directory. Each successful re-summarisation SHALL be appended (not overwritten) as a new entry in the `summaries` list in `memory_summaries.json`, each containing `date` (ISO-8601), `text` (the condensed block), and `observation_count` (how many observations it condenses). The `summaries` list SHALL be capped at a configurable maximum (`memory_summary_history_max`, default 200); when the cap is reached the oldest summaries SHALL be pruned before appending new ones. `summarise()` SHALL build the coach's notes from the *most recent* entry in `summaries` (if any) plus any raw observations appended since that entry's date — not by concatenating multiple summaries.

#### Scenario: Condensation appends rather than overwrites
- **WHEN** a re-summarisation pass succeeds and prior summaries already exist
- **THEN** the new condensed block is appended as a new entry in `memory_summaries.json`, and prior entries remain unchanged

#### Scenario: Summary history cap exceeded — oldest pruned
- **WHEN** appending a new summary would bring the `summaries` total above the configured `memory_summary_history_max` (default 200)
- **THEN** the oldest summary entries are removed before the new one is appended so the total stays at the configured cap

#### Scenario: Only the most recent summary is sent to the LLM
- **WHEN** the coach's notes block is built and `summaries` has more than one entry
- **THEN** the block is based on the most recent entry only, plus raw observations appended since that entry's date — older summaries are not concatenated in

#### Scenario: Observations and summaries load and persist independently
- **WHEN** `memory.json` exists but `memory_summaries.json` does not (or vice versa)
- **THEN** the missing file is treated as empty and does not prevent the other file's contents from loading; appending an observation does not rewrite `memory_summaries.json`, and appending a summary does not rewrite `memory.json`

#### Scenario: Clearing memory resets both files
- **WHEN** the user clears all memory (e.g. via the Memory Viewer's "Clear All Memory")
- **THEN** both `memory.json` and `memory_summaries.json` are emptied, and the re-summarisation counter is reset

### Requirement: Observation cap, summary-history cap, and re-summarisation interval are user-configurable via Settings
`memory_max_observations`, `memory_summary_history_max`, and `memory_resummarize_interval` SHALL all be editable from the Settings dialog, so the user does not need to hand-edit `config.json` to change any of these values.

#### Scenario: User changes the observation cap
- **WHEN** the user opens Settings, changes the maximum stored observations, and saves
- **THEN** the new cap is persisted to `config.json` and used by subsequent `MemoryStore.append` calls

#### Scenario: User changes the summary-history cap
- **WHEN** the user opens Settings, changes the maximum stored summary-history entries, and saves
- **THEN** the new cap is persisted to `config.json` and used the next time a summary is appended to `summaries`
