## ADDED Requirements

### Requirement: Persist drawing observations to memory.json
The system SHALL maintain a `memory.json` file in the app data directory that persists across sessions. The file SHALL store a list of observations, each containing `date` (ISO-8601), `session_id` (string), `category` (string, e.g. `anatomy`, `perspective`, `line_quality`), and `note` (short string). The total number of stored observations SHALL be capped at 200; when the cap is reached the oldest observations SHALL be pruned before appending new ones.

#### Scenario: First observation written to new file
- **WHEN** an observation is appended and `memory.json` does not yet exist
- **THEN** the file is created and contains the new observation

#### Scenario: Observation appended to existing file
- **WHEN** an observation is appended and `memory.json` already has entries
- **THEN** the new observation is added and the file is saved

#### Scenario: Cap exceeded — oldest pruned
- **WHEN** appending an observation would bring the total above 200
- **THEN** the oldest observation(s) are removed before the new one is appended so the total stays at 200

#### Scenario: Memory loaded on startup
- **WHEN** the application starts and `memory.json` exists
- **THEN** all stored observations are loaded into `MemoryStore` and available for prompt injection and the UI

### Requirement: Extract observations from LLM response text
After each feedback response the system SHALL attempt to parse a `<!-- observations: [...] -->` HTML comment from the response text containing a JSON array of `{category, note}` objects. Successfully parsed observations SHALL be appended to the store with the current date and session ID. If the comment is absent or malformed no observations are recorded and no error is shown to the user.

#### Scenario: Valid observations comment present
- **WHEN** an LLM response includes a well-formed `<!-- observations: [...] -->` comment
- **THEN** the observations are parsed, appended to the store, and the comment is stripped from the displayed feedback text

#### Scenario: Observations comment absent
- **WHEN** an LLM response contains no `<!-- observations: -->` comment
- **THEN** no observations are recorded and the response text is displayed as-is

#### Scenario: Malformed observations comment
- **WHEN** an LLM response contains a `<!-- observations: -->` comment with invalid JSON
- **THEN** no observations are recorded, a debug log entry is written, and the comment is stripped from the displayed text
