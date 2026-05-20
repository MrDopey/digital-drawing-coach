## MODIFIED Requirements

### Requirement: Periodic screenshot capture
The system SHALL capture a screenshot of the selected drawing window at a user-configurable interval (default: 30 seconds, range: 5–300 seconds). Captures SHALL be stored to disk under a per-session directory (`~/.drawing-coach/sessions/<session-id>/frames/`). Near-duplicate frames SHALL be dropped before writing using a configurable MAE deduplication threshold (default: 2.0, independently configurable from the stuck-detection threshold).

#### Scenario: Capture runs on schedule
- **WHEN** a drawing window is selected and capture is active
- **THEN** the system captures a screenshot of that window at each interval tick

#### Scenario: Duplicate frame is detected and dropped
- **WHEN** a newly captured frame has MAE below the deduplication threshold compared to the last stored frame
- **THEN** the system discards the new frame without writing to disk and without updating the session history view

#### Scenario: Non-duplicate frame is stored
- **WHEN** a newly captured frame has MAE above the deduplication threshold
- **THEN** the system writes the frame to disk as a PNG with a timestamp filename and adds it to the session history view

#### Scenario: Capture interval changed by user
- **WHEN** the user updates the capture interval in settings
- **THEN** the system applies the new interval on the next tick without restarting the session

### Requirement: Session history is persisted to disk
The system SHALL write each accepted frame immediately to disk so that session history survives application restarts. On startup, the system SHALL load the most recent session's frames back into the history view if the session was started within the last 24 hours.

#### Scenario: Application is restarted mid-session
- **WHEN** the application is closed and reopened within 24 hours of the last session start
- **THEN** the session history view shows the previously captured frames from disk

#### Scenario: Session is older than 24 hours
- **WHEN** the application starts and the most recent on-disk session is older than 24 hours
- **THEN** the system starts a new session directory and the history view starts empty

### Requirement: Session history auto-cleans to retain last N sessions
The system SHALL delete the oldest session directories on startup until only the configured number of sessions remain (default: 10, range: 1–100). Deletion is permanent with no recycle bin.

#### Scenario: Retention limit is not exceeded
- **WHEN** the application starts and the number of session directories is at or below the configured limit
- **THEN** no session directories are deleted

#### Scenario: Retention limit is exceeded
- **WHEN** the application starts and the number of session directories exceeds the configured limit
- **THEN** the system deletes the oldest session directories (by creation time) until only the configured limit remains, before loading the current session

#### Scenario: User changes retention limit
- **WHEN** the user lowers the retention limit in settings and saves
- **THEN** the system immediately applies cleanup, deleting excess sessions beyond the new limit

### Requirement: Session history is viewable
The system SHALL present a visual timeline of captured frames within the current session so the user can review their progress.

#### Scenario: User opens session history
- **WHEN** the user clicks "Session History"
- **THEN** the system displays thumbnails of all stored frames for the current session in chronological order with timestamps

#### Scenario: History is empty
- **WHEN** the user opens session history before any non-duplicate captures have been stored
- **THEN** the system displays an empty state message
