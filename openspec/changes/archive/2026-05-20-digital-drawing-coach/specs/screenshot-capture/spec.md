## ADDED Requirements

### Requirement: Periodic screenshot capture
The system SHALL capture a screenshot of the selected drawing window at a user-configurable interval (default: 30 seconds, range: 5–300 seconds). Captures SHALL be stored in an in-memory ring buffer limited to the last 20 frames.

#### Scenario: Capture runs on schedule
- **WHEN** a drawing window is selected and capture is active
- **THEN** the system captures a screenshot of that window at each interval tick

#### Scenario: Buffer is full
- **WHEN** the ring buffer reaches its maximum capacity (20 frames)
- **THEN** the system discards the oldest frame and adds the new capture

#### Scenario: Capture interval changed by user
- **WHEN** the user updates the capture interval in settings
- **THEN** the system applies the new interval on the next tick without restarting the session

### Requirement: Capture can be paused and resumed
The system SHALL allow the user to pause and resume screenshot capture without losing the existing session history.

#### Scenario: User pauses capture
- **WHEN** the user clicks "Pause" in the main UI
- **THEN** the system stops scheduling new captures and shows a "Paused" status indicator

#### Scenario: User resumes capture
- **WHEN** the user clicks "Resume" after pausing
- **THEN** the system restarts the capture schedule and continues appending to the existing buffer

### Requirement: Session history is viewable
The system SHALL present a visual timeline of captured frames within the current session so the user can review their progress.

#### Scenario: User opens session history
- **WHEN** the user clicks "Session History"
- **THEN** the system displays thumbnails of all buffered captures in chronological order with timestamps

#### Scenario: History is empty
- **WHEN** the user opens session history before any captures have been taken
- **THEN** the system displays an empty state message
