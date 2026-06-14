## ADDED Requirements

### Requirement: Check result messages are selectable
Each check row's message and hint text SHALL be selectable and copyable by the user using mouse or keyboard.

#### Scenario: User selects error text with mouse
- **WHEN** a check row shows a failure message
- **THEN** the user can click and drag over the message text to select it and copy it to the clipboard via Ctrl+C / Cmd+C

#### Scenario: Message label has text-interaction flags set
- **WHEN** `DiagnosticsDialog` creates each message label
- **THEN** the label has `TextSelectableByMouse` and `TextSelectableByKeyboard` interaction flags set

### Requirement: Copy Report button
The dialog SHALL provide a "Copy Report" button that copies all completed check results to the system clipboard as plain text.

#### Scenario: Copy Report produces plain-text summary
- **WHEN** all checks have finished and the user clicks "Copy Report"
- **THEN** the clipboard contains one line per check: `[✓]` or `[✗]` followed by the check name, an em-dash, and the message; if the check failed and has a hint, the next line is indented with `Hint: <hint text>`

#### Scenario: Copy Report button is disabled while checks are running
- **WHEN** checks are still in progress
- **THEN** the "Copy Report" button is disabled

#### Scenario: Copy Report button enables when all checks finish
- **WHEN** all checks have completed (all_done signal fires)
- **THEN** the "Copy Report" button becomes enabled

### Requirement: Dialog opens sized to show all check rows
The dialog SHALL size itself on first launch so that all (or most) check rows are visible without scrolling, using `adjustSize()` rather than a hardcoded height. The check rows SHALL be wrapped in a `QScrollArea` so the dialog remains usable if the content exceeds the available screen height.

#### Scenario: Dialog height fits content on launch
- **WHEN** the DiagnosticsDialog is opened for the first time
- **THEN** the dialog height is large enough to display all check rows without the user needing to scroll or resize

#### Scenario: Dialog is scrollable if content overflows
- **WHEN** the number of check rows exceeds the available height
- **THEN** a scroll bar appears and all rows remain accessible
