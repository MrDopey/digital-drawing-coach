## MODIFIED Requirements

### Requirement: Capture can be paused and resumed

The system SHALL allow the user to pause and resume screenshot capture without losing the existing session history. The pause/resume control (main window button and system tray menu action) SHALL be disabled and SHALL display the paused-state label whenever no drawing window is currently targeted for capture — including at application startup before any window has been selected, and after the previously targeted window is lost or closed. The control SHALL become enabled only once a drawing window has been successfully selected as the capture target.

#### Scenario: No window selected at startup
- **WHEN** the application starts and no drawing window has been selected yet
- **THEN** the pause/resume control displays the paused-state label ("Resume") and is disabled

#### Scenario: Window is selected
- **WHEN** the user selects a drawing window via "Select Window"
- **THEN** the pause/resume control becomes enabled and reflects the active capture state ("Pause")

#### Scenario: Target window is lost
- **WHEN** the monitored drawing window is closed or becomes unavailable
- **THEN** the system pauses capture and the pause/resume control returns to the disabled, paused-state label ("Resume") until a new window is selected

#### Scenario: User pauses capture
- **WHEN** the user clicks "Pause" in the main UI while a window is targeted
- **THEN** the system stops scheduling new captures and shows a "Paused" status indicator

#### Scenario: User resumes capture
- **WHEN** the user clicks "Resume" after pausing while a window is targeted
- **THEN** the system restarts the capture schedule and continues appending to the existing buffer
