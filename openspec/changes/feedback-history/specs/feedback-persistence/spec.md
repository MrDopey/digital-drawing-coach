## ADDED Requirements

### Requirement: Save feedback response to disk on arrival
When a `FeedbackResponse` is received the system SHALL save it to disk as a JSON file at `feedback/<session-id>/YYYYMMDD_HHMMSS_<mode>.json`. The JSON SHALL include: `mode`, `text`, `timestamp` (ISO-8601), `frame_hashes` (list of SHA-256 hex strings), `annotation_json` (null if not overlay mode), and `thumbnail_path` (relative path to the saved thumbnail). A thumbnail of the last frame used SHALL be saved alongside as `YYYYMMDD_HHMMSS_<mode>_thumb.jpg` scaled to 160×120.

#### Scenario: Feedback response saved on arrival
- **WHEN** a `FeedbackResponse` is received from the LLM
- **THEN** a JSON file is written to the session's feedback directory within one second of arrival

#### Scenario: Thumbnail saved alongside JSON
- **WHEN** a feedback JSON file is saved
- **THEN** a 160×120 JPEG thumbnail of the last frame used is saved in the same directory with the `_thumb.jpg` suffix

#### Scenario: Save directory created automatically
- **WHEN** the feedback directory does not yet exist for the current session
- **THEN** the system creates it before writing the first entry

### Requirement: Load session feedback history on startup
On startup, the system SHALL read all JSON files in the current session's feedback directory (in filename order) and make them available in the feedback panel history list.

#### Scenario: History loaded on startup
- **WHEN** the application starts and the active session has saved feedback entries
- **THEN** those entries are available immediately in the feedback panel without generating new feedback

#### Scenario: No saved history for session
- **WHEN** the application starts and no feedback files exist for the active session
- **THEN** the feedback panel history list is empty and no error occurs
