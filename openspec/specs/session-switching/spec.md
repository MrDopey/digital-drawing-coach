# session-switching Specification

## Purpose
TBD - created by syncing change session-management. Update Purpose after archive.
## Requirements
### Requirement: Sessions menu in the main window
The main window SHALL provide a Sessions menu (in the menu bar or as a toolbar button) that lists all saved sessions and a New Session action. The active session name SHALL be shown in the title bar as `Drawing Coach — <session name>`.

#### Scenario: Sessions menu lists all sessions
- **WHEN** the user opens the Sessions menu
- **THEN** it lists the active session (greyed, non-clickable) at the top, all other sessions by name (newest first), a separator, and a New Session action

#### Scenario: Title bar shows active session name
- **WHEN** a session is active
- **THEN** the window title bar reads `Drawing Coach — <session name>`

#### Scenario: Title bar updates after rename
- **WHEN** the user renames the active session
- **THEN** the title bar updates immediately to show the new name

### Requirement: In-app session switching
The system SHALL allow the user to switch to another session or start a new one from within the main window without restarting the application. Switching SHALL save the current session state (end_time in meta.json) before loading the selected session.

#### Scenario: User switches to an existing session
- **WHEN** the user selects a different session from the Sessions menu
- **THEN** the current session's end_time is written to its meta.json, capture stops, the selected session is loaded, its frames appear in the history panel, and capture restarts

#### Scenario: User creates a new session from the main window
- **WHEN** the user clicks New Session in the Sessions menu
- **THEN** a new session directory is created, the history panel clears, capture restarts on the new session, and the title bar updates to show the new session name
