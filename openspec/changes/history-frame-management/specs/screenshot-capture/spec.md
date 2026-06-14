## MODIFIED Requirements

### Requirement: Session history is persisted to disk
The system SHALL write each accepted frame immediately to disk so that session history survives application restarts. On startup, the system SHALL load the most recent session's frames back into the history view if the session was started within the last 24 hours. The engine SHALL expose a `remove_frame(frame: CapturedFrame)` method that removes a frame from the in-memory buffer without deleting its file from disk. After any buffer mutation the engine SHALL emit a `frames_changed` signal so subscribers (e.g. the history panel) can update.

#### Scenario: Application is restarted mid-session
- **WHEN** the application is closed and reopened within 24 hours of the last session start
- **THEN** the session history view shows the previously captured frames from disk

#### Scenario: Session is older than 24 hours
- **WHEN** the application starts and the most recent on-disk session is older than 24 hours
- **THEN** the system starts a new session directory and the history view starts empty

#### Scenario: Frame removed from buffer via remove_frame
- **WHEN** `CaptureEngine.remove_frame(frame)` is called with a frame that is in the buffer
- **THEN** the frame is removed from `_buffer`, its PNG file on disk is NOT deleted, and `frames_changed` is emitted

#### Scenario: frames_changed emitted on new capture
- **WHEN** a new frame is appended to `_buffer`
- **THEN** the `frames_changed` signal is emitted
