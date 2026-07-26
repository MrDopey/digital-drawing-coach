## ADDED Requirements

### Requirement: Inject coach's notes into LLM system prompt
Before each LLM feedback request the system SHALL summarise recent observations from `MemoryStore` into a short "coach's notes" block and append it to the *end* of the system prompt (after the base persona, style fragment, custom instructions, and mode template). The block SHALL include up to 20 recent observations and the total number of sessions the user has had (derived from `sessions_dir()`). The block SHALL be omitted when the memory store is empty.

The notes block SHALL be appended rather than prepended so that the persona/style/custom-instructions/mode-template prefix remains byte-identical across requests, preserving provider-side prompt-cache hits on that prefix.

#### Scenario: Memory store has observations
- **WHEN** a feedback request is made and the memory store contains at least one observation
- **THEN** the system prompt includes a coach's notes block appended after the base coaching prompt, style fragment, custom instructions, and mode template

#### Scenario: Memory store is empty
- **WHEN** a feedback request is made and the memory store has no observations
- **THEN** the system prompt does not include a coach's notes block and is identical to the prompt sent on first use

#### Scenario: Session count included in notes block
- **WHEN** the coach's notes block is generated
- **THEN** it includes a statement indicating how many sessions the user has had (e.g. "You have worked with this student across 5 sessions.")

#### Scenario: Notes block capped at 20 most recent observations
- **WHEN** the memory store has more than 20 observations
- **THEN** only the 20 most recent are included in the coach's notes block sent to the LLM

### Requirement: Coach's notes are periodically re-summarised by default; this is the exact content injected for advice
The coach's notes block is the content injected into the LLM system prompt to produce coaching advice, so it SHALL be kept compact via periodic LLM condensation rather than left to grow raw and unbounded. A config field `memory_resummarize_interval` (default `20`) SHALL control the cadence: once that many observations have been appended since the last re-summarisation, the next coach's-notes build SHALL trigger one LLM call that condenses the accumulated raw notes into a shorter block. That block is appended to a persisted summary history (see the `memory-store` capability) and, from then on, the coach's notes are built from the *most recent* summary in that history plus any raw observations appended since — until the threshold is reached again. Setting `memory_resummarize_interval` to `0` SHALL opt out entirely, keeping notes raw forever.

#### Scenario: Default behavior re-summarises every 20 responses
- **WHEN** `memory_resummarize_interval` is left at its default (`20`) and 20 observations have been appended since the last re-summarisation
- **THEN** the next coach's-notes build triggers an LLM call that condenses the accumulated raw notes into a shorter block

#### Scenario: Notes are raw between condensation passes
- **WHEN** fewer observations have been appended since the last re-summarisation than `memory_resummarize_interval`
- **THEN** the coach's notes block is built by formatting the raw observations, with no LLM call made to produce it

#### Scenario: Re-summarisation threshold reached
- **WHEN** `memory_resummarize_interval` is set to `N > 0` and `N` observations have been appended since the last re-summarisation (or since the store was created)
- **THEN** the next coach's-notes build triggers an LLM call that condenses the accumulated raw notes into a shorter block, that block is appended to the summary history, and it becomes the basis of the coach's notes going forward

#### Scenario: User opts out of re-summarisation
- **WHEN** `memory_resummarize_interval` is set to `0`
- **THEN** the coach's notes block is always built by formatting raw observations, with no LLM call ever made to produce it

#### Scenario: Re-summarisation call fails
- **WHEN** the periodic re-summarisation LLM call fails or times out
- **THEN** the existing raw or previously-summarised notes are used unchanged, a debug log entry is written, and the feedback request proceeds without blocking on the failure

### Requirement: Re-summarisation cadence is user-configurable via Settings
The system SHALL expose `memory_resummarize_interval` as an editable control in the Settings dialog (alongside the existing LLM/Capture/Stuck Detection/History settings), so the user does not need to hand-edit `config.json` to change or disable the re-summarisation cadence.

#### Scenario: User changes the re-summarisation interval
- **WHEN** the user opens Settings, changes the coach's-notes re-summarisation interval, and saves
- **THEN** the new value is persisted to `config.json` and used for subsequent coach's-notes builds

#### Scenario: User disables re-summarisation via Settings
- **WHEN** the user sets the re-summarisation interval to `0` in Settings and saves
- **THEN** subsequent coach's-notes builds use raw observations only and never trigger a condensation LLM call
