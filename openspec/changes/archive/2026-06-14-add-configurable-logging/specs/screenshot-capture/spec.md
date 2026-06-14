## ADDED Requirements

### Requirement: Session directory is logged at startup
The system SHALL emit an INFO log when a session is created or resumed, stating the full path of the session directory so users can locate their screenshots.

#### Scenario: New session created
- **WHEN** `CaptureEngine.start()` initialises a new session
- **THEN** an INFO log is emitted: `New session: <absolute_path>`

#### Scenario: Existing session resumed
- **WHEN** `CaptureEngine.start()` resumes a session started within 24 hours
- **THEN** an INFO log is emitted: `Resumed session: <absolute_path> (<N> existing frames)`

#### Scenario: Old sessions pruned
- **WHEN** the engine prunes session directories to enforce the retention limit
- **THEN** an INFO log is emitted: `Pruned <N> old sessions (retention: <K>)`

### Requirement: Frame capture outcomes are logged at DEBUG
The system SHALL emit a DEBUG log for each frame capture attempt indicating whether the frame was saved or skipped.

#### Scenario: Frame is saved to disk
- **WHEN** a frame passes deduplication and is written to disk
- **THEN** a DEBUG log is emitted: `Frame saved: <filename> (<W>x<H>)`

#### Scenario: Frame is skipped due to deduplication
- **WHEN** a frame's MAE is below the deduplication threshold
- **THEN** a DEBUG log is emitted: `Frame skipped: MAE=<val:.2f> < threshold=<val:.2f>`

### Requirement: Window loss is logged at WARNING
The system SHALL emit a WARNING log when the tracked drawing window can no longer be found.

#### Scenario: Drawing window disappears
- **WHEN** `get_window_rect` returns None for the tracked window
- **THEN** a WARNING log is emitted: `Drawing window lost — capture paused`

### Requirement: Capture pause and resume are logged at INFO
The system SHALL emit INFO logs when capture is paused or resumed by the user.

#### Scenario: User pauses capture
- **WHEN** `CaptureEngine.pause()` is called
- **THEN** an INFO log is emitted: `Capture paused by user`

#### Scenario: User resumes capture
- **WHEN** `CaptureEngine.resume()` is called
- **THEN** an INFO log is emitted: `Capture resumed`
