## MODIFIED Requirements

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
