# diagnostics-copyable-results Specification

## Purpose
TBD - created by archiving change editable-diagnostics-dialog. Update Purpose after archive.
## Requirements
### Requirement: Diagnostics results are selectable and copyable
The DiagnosticsDialog SHALL display check results with selectable text so the user can copy individual lines, and SHALL provide a "Copy Report" button that copies the full diagnostics report to the system clipboard as plain text.

#### Scenario: User selects and copies a single result line
- **WHEN** the DiagnosticsDialog has finished running checks
- **THEN** the user can click and drag to select text within any result row and copy it with the standard OS copy shortcut

#### Scenario: User clicks "Copy Report"
- **WHEN** the DiagnosticsDialog has finished running checks and the user clicks "Copy Report"
- **THEN** the full diagnostics report — including each check name, status (pass/fail), message, and any hint — is copied to the system clipboard as plain text

#### Scenario: "Copy Report" is available during and after checks
- **WHEN** the DiagnosticsDialog is open (whether checks are running or complete)
- **THEN** the "Copy Report" button is visible and clickable at all times
