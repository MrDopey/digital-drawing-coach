## MODIFIED Requirements

### Requirement: Diagnostics dialog accessible from Settings
The system SHALL provide a "Diagnostics…" button in the Settings dialog that opens a DiagnosticsDialog showing the status of all system health checks. The dialog SHALL display check results with selectable text and a "Copy Report" button.

#### Scenario: User opens diagnostics from Settings
- **WHEN** the user opens the Settings dialog and clicks the "Diagnostics…" button
- **THEN** a non-modal DiagnosticsDialog opens and immediately begins running checks

#### Scenario: Dialog can be re-run
- **WHEN** the DiagnosticsDialog is already open and the user clicks "Re-run"
- **THEN** all check rows reset to pending state and the checks execute again from the beginning
