# session-picker Specification

## Purpose
TBD - created by syncing change session-management. Update Purpose after archive.
## Requirements
### Requirement: Launch-time session picker dialog
The system SHALL display a session picker dialog before the main window opens when at least one saved session exists. The dialog SHALL list all saved sessions in reverse-chronological order. Each entry SHALL show the session name, start date/time, and a thumbnail image (the last captured frame PNG from `frames/`). When no sessions exist the picker SHALL be skipped and the app SHALL start a new session directly.

#### Scenario: One or more sessions exist on launch
- **WHEN** the application starts and at least one session directory with a `meta.json` exists on disk
- **THEN** the session picker dialog is shown before the main window

#### Scenario: No sessions exist on launch
- **WHEN** the application starts and no session directories exist on disk
- **THEN** the picker dialog is skipped and the app opens directly with a new session

#### Scenario: Session entry shows name, date, and thumbnail
- **WHEN** the session picker lists a session
- **THEN** each row shows the session name, the start date/time, and a thumbnail (120×80) of the last frame PNG

#### Scenario: Thumbnail expands on hover
- **WHEN** the user hovers over a session entry thumbnail
- **THEN** a larger preview (360×240) of the frame is shown as a tooltip or floating overlay

### Requirement: Picker actions — Resume, New Session, Delete
The session picker SHALL provide three actions: Resume the selected session, start a New Session, and Delete the selected session. Deleting a session SHALL ask for confirmation before removing the session directory from disk.

#### Scenario: User resumes a session
- **WHEN** the user selects a session and clicks Resume (or double-clicks the entry)
- **THEN** the main window opens with that session loaded and its frames available in history

#### Scenario: User starts a new session
- **WHEN** the user clicks New Session in the picker
- **THEN** the picker closes, a new session directory is created, and the main window opens with an empty history

#### Scenario: User deletes a session
- **WHEN** the user selects a session and clicks Delete
- **THEN** a confirmation dialog is shown; on confirm the session directory is removed from disk and the entry disappears from the list; on cancel nothing changes

#### Scenario: User quits from the picker
- **WHEN** the user closes the picker dialog without choosing an action
- **THEN** the application exits without opening the main window
