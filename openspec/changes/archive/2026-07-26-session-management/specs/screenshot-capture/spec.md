## MODIFIED Requirements

### Requirement: Session history is persisted to disk
The system SHALL write each accepted frame immediately to disk so that session history survives application restarts. On startup, when no session has been explicitly selected via the session picker, the system SHALL load the most recent session's frames back into the history view if the session was started within the last 24 hours. `meta.json` SHALL include a `name` field (string); if absent the system derives a display label from `start_time`.

#### Scenario: Application is restarted mid-session
- **WHEN** the application is closed and reopened within 24 hours of the last session start
- **THEN** the session history view shows the previously captured frames from disk

#### Scenario: Session is older than 24 hours
- **WHEN** the application starts and the most recent on-disk session is older than 24 hours
- **THEN** the system starts a new session directory and the history view starts empty

#### Scenario: meta.json written with name on session create
- **WHEN** a new session directory is created
- **THEN** `meta.json` is written with `start_time` and `name` fields; `name` is the timestamp-derived default label
