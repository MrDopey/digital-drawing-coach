# feedback-persistence Specification

## Purpose
TBD - created by archiving change feedback-history. Update Purpose after archive.

## Requirements
### Requirement: Save feedback response to disk on arrival
When a `FeedbackResponse` is received the system SHALL save it to disk as a JSON file at `feedback/<session-id>/YYYYMMDD_HHMMSS_<mode>.json`. The JSON SHALL include: `mode`, `text`, `timestamp` (ISO-8601), `frame_hashes` (list of SHA-256 hex strings), `annotation_json` (null if not overlay mode), `observations` (list of category/note objects), `used_structured_output` (boolean), and `frame_path` (path to the full-resolution captured frame the feedback was based on, or null when no frame was available). The `frame_path` SHALL reference the already-captured frame file under the session's `frames/` directory — no additional full-resolution copy is written. The system SHALL NOT write a downscaled thumbnail of the frame, and the JSON SHALL NOT carry a `thumbnail_path` field. When the response's mode is `overlay`, the composited annotated image SHALL additionally be saved alongside as `YYYYMMDD_HHMMSS_<mode>_overlay.png` at full resolution, so it can still be viewed, zoomed, and saved after the app restarts.

#### Scenario: Feedback response saved on arrival
- **WHEN** a `FeedbackResponse` is received from the LLM
- **THEN** a JSON file is written to the session's feedback directory within one second of arrival

#### Scenario: No thumbnail is written
- **WHEN** a feedback JSON file is saved
- **THEN** no `_thumb.jpg` file is created in the feedback directory and the JSON contains no `thumbnail_path` field

#### Scenario: Full-resolution frame recorded in the JSON
- **WHEN** a feedback response is saved and the last frame used has a file on disk
- **THEN** the entry JSON records that frame's path in `frame_path`, and no additional full-resolution image file is written

#### Scenario: No frame available when saving
- **WHEN** a feedback response is saved and no last frame is available
- **THEN** the entry JSON records `frame_path` as null and the save completes without error

#### Scenario: Overlay entries also save the composited image
- **WHEN** an overlay-mode `FeedbackResponse` is saved and a composited annotated image is available
- **THEN** the full-resolution composited image is saved alongside the JSON with the `_overlay.png` suffix

#### Scenario: Save directory created automatically
- **WHEN** the feedback directory does not yet exist for the current session
- **THEN** the system creates it before writing the first entry

### Requirement: Load session feedback history on startup and on session change
On startup, and whenever the active session changes (a new session is started, or the user switches sessions via the Sessions menu), the system SHALL read all JSON files in that session's feedback directory (in filename order), reconstruct their saved overlay images where present, resolve each entry's recorded full-resolution `frame_path` where the file still exists on disk, and make them available in the feedback panel's sidebar — replacing whatever was previously loaded. An entry whose JSON has no `frame_path`, or whose referenced frame file no longer exists, SHALL still load successfully with no full-resolution image resolved.

#### Scenario: History loaded on startup
- **WHEN** the application starts and the active session has saved feedback entries
- **THEN** those entries are available immediately in the feedback panel without generating new feedback

#### Scenario: History reloaded after switching sessions
- **WHEN** the user switches to a different session via the Sessions menu
- **THEN** the feedback panel's sidebar replaces the previous session's entries with the newly active session's saved entries

#### Scenario: Entry saved before frame paths were recorded
- **WHEN** an entry JSON written by an older version of the app (with no `frame_path` field, and carrying a now-unused `thumbnail_path` field) is loaded
- **THEN** the entry loads successfully with no full-resolution frame resolved, the obsolete `thumbnail_path` is ignored, and no error is raised

#### Scenario: Referenced frame file has been removed
- **WHEN** an entry records a `frame_path` whose file no longer exists on disk
- **THEN** the entry loads successfully with no full-resolution frame resolved, and no error is raised

#### Scenario: No saved history for session
- **WHEN** the application starts (or switches to a session) and no feedback files exist for that session
- **THEN** the feedback panel's sidebar is empty and no error occurs

### Requirement: Derive missing frame hashes from the frame image on disk
When loading a feedback entry whose JSON records no `frame_hashes` (an entry written before frame-hash tracking existed, or one whose list is empty), the system SHALL derive its frame hashes from the full-resolution frame image referenced by `frame_path`, when that file still exists on disk. The derived hashes SHALL use the same scheme as the live capture path — the SHA-256 hex digest of the decoded image's raw bytes — so a derived hash and a live hash of the same image are equal. Derivation SHALL happen in memory at load time; the system SHALL NOT rewrite the entry's JSON on disk.

When an entry has no recorded hashes and no resolvable `frame_path`, or the frame image cannot be decoded, its frame hashes SHALL be treated as unknown — never as a fingerprint that can match a current frame set (see `feedback-deduplication`) — and the entry SHALL load successfully with all its other content intact.

#### Scenario: Entry with no recorded hashes but a resolvable frame
- **WHEN** an entry JSON has no `frame_hashes` and its `frame_path` references a frame file that still exists
- **THEN** the entry loads with frame hashes derived from that image, equal to the hash the live capture path would produce for the same image

#### Scenario: Derived hashes are not written back
- **WHEN** an entry's frame hashes have been derived from disk
- **THEN** the entry's JSON file on disk is left byte-for-byte unchanged

#### Scenario: Entry with no recorded hashes and no frame on disk
- **WHEN** an entry JSON has no `frame_hashes` and either no `frame_path` or one whose file no longer exists
- **THEN** the entry loads with its frame hashes treated as unknown, and its text, mode, timestamp, and observations are unaffected

#### Scenario: Undecodable frame image
- **WHEN** an entry has no recorded hashes and its `frame_path` references a file that cannot be decoded as an image
- **THEN** the failure is logged, the entry loads with its frame hashes treated as unknown, and loading of the remaining entries continues

#### Scenario: Recorded hashes are left alone
- **WHEN** an entry JSON already records a non-empty `frame_hashes` list
- **THEN** those hashes are used as-is and no frame image is decoded for it
