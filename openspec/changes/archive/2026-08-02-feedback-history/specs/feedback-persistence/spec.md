## ADDED Requirements

### Requirement: Save feedback response to disk on arrival
When a `FeedbackResponse` is received the system SHALL save it to disk as a JSON file at `feedback/<session-id>/YYYYMMDD_HHMMSS_<mode>.json`. The JSON SHALL include: `mode`, `text`, `timestamp` (ISO-8601), `frame_hashes` (list of SHA-256 hex strings), `annotation_json` (null if not overlay mode), `observations` (list of category/note objects), `used_structured_output` (boolean), and `thumbnail_path` (relative path to the saved thumbnail). A thumbnail of the last frame used SHALL be saved alongside as `YYYYMMDD_HHMMSS_<mode>_thumb.jpg` scaled to 160×160. When the response's mode is `overlay`, the composited annotated image SHALL additionally be saved alongside as `YYYYMMDD_HHMMSS_<mode>_overlay.png` at full resolution, so it can still be viewed, zoomed, and saved after the app restarts.

#### Scenario: Feedback response saved on arrival
- **WHEN** a `FeedbackResponse` is received from the LLM
- **THEN** a JSON file is written to the session's feedback directory within one second of arrival

#### Scenario: Thumbnail saved alongside JSON
- **WHEN** a feedback JSON file is saved
- **THEN** a 160×160 JPEG thumbnail of the last frame used is saved in the same directory with the `_thumb.jpg` suffix

#### Scenario: Overlay entries also save the composited image
- **WHEN** an overlay-mode `FeedbackResponse` is saved and a composited annotated image is available
- **THEN** the full-resolution composited image is saved alongside the JSON with the `_overlay.png` suffix

#### Scenario: Save directory created automatically
- **WHEN** the feedback directory does not yet exist for the current session
- **THEN** the system creates it before writing the first entry

### Requirement: Load session feedback history on startup and on session change
On startup, and whenever the active session changes (a new session is started, or the user switches sessions via the Sessions menu), the system SHALL read all JSON files in that session's feedback directory (in filename order), reconstruct their saved overlay images where present, and make them available in the feedback panel's sidebar — replacing whatever was previously loaded.

#### Scenario: History loaded on startup
- **WHEN** the application starts and the active session has saved feedback entries
- **THEN** those entries are available immediately in the feedback panel without generating new feedback

#### Scenario: History reloaded after switching sessions
- **WHEN** the user switches to a different session via the Sessions menu
- **THEN** the feedback panel's sidebar replaces the previous session's entries with the newly active session's saved entries

#### Scenario: No saved history for session
- **WHEN** the application starts (or switches to a session) and no feedback files exist for that session
- **THEN** the feedback panel's sidebar is empty and no error occurs
