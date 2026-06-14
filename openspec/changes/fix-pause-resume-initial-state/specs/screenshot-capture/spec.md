## MODIFIED Requirements

### Requirement: Capture can be paused and resumed
The system SHALL allow the user to pause and resume screenshot capture without losing the existing session history. Before a drawing window has been selected, the pause/resume control SHALL display a "Start Capture" state that opens the window picker when activated. Once a drawing window is selected and capture is active, the control transitions to the normal Pause / Resume cycle. The system tray action SHALL reflect the same three-state logic.

#### Scenario: No window selected on launch — button shows Start Capture
- **WHEN** the application starts and no drawing window has been selected
- **THEN** the pause/resume button displays "Start Capture" and the tray action displays "Select Window"

#### Scenario: Clicking Start Capture opens window picker
- **WHEN** the user clicks the "Start Capture" button before selecting a drawing window
- **THEN** the window selection dialog opens

#### Scenario: Window selected — button transitions to Pause
- **WHEN** the user selects a drawing window
- **THEN** the button label changes to "Pause" and the tray action changes to "Pause Capture"

#### Scenario: User pauses capture
- **WHEN** the user clicks "Pause" in the main UI after a window has been selected
- **THEN** the system stops scheduling new captures and shows a "Paused" status indicator

#### Scenario: User resumes capture
- **WHEN** the user clicks "Resume" after pausing
- **THEN** the system restarts the capture schedule and continues appending to the existing buffer
