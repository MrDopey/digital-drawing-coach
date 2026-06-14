## ADDED Requirements

### Requirement: Memory viewer shows all observations grouped by category
The system SHALL provide a memory viewer dialog accessible from the main window (e.g. via a Settings or Tools menu). The viewer SHALL list all stored observations in reverse-chronological order, grouped by category. Each observation row SHALL show its date and note text. The viewer SHALL also display the current coach's notes summary (read-only text area) at the top.

#### Scenario: Memory viewer opened with observations
- **WHEN** the user opens the memory viewer and observations exist
- **THEN** observations are displayed grouped by category in reverse-chronological order

#### Scenario: Memory viewer opened with no observations
- **WHEN** the user opens the memory viewer and no observations exist
- **THEN** the viewer shows an empty state message (e.g. "No observations recorded yet")

### Requirement: Delete individual observations from memory viewer
Each observation row in the memory viewer SHALL have a delete button. Activating it SHALL remove that observation from the store immediately and refresh the viewer.

#### Scenario: User deletes an observation
- **WHEN** the user clicks the delete button on an observation row
- **THEN** the observation is removed from `memory.json` and disappears from the viewer

### Requirement: Clear all memory with confirmation
The memory viewer SHALL provide a "Clear All Memory" button. Activating it SHALL show a confirmation dialog before deleting all observations. On confirmation all observations are removed from `memory.json`.

#### Scenario: User confirms clear all
- **WHEN** the user clicks Clear All Memory and confirms the dialog
- **THEN** all observations are removed from `memory.json` and the viewer shows the empty state

#### Scenario: User cancels clear all
- **WHEN** the user clicks Clear All Memory but cancels the confirmation dialog
- **THEN** no observations are removed and the viewer is unchanged

### Requirement: Export memory to user-chosen location
The memory viewer SHALL provide an "Export Memory" button that opens a save-file dialog and copies `memory.json` to the user-chosen path.

#### Scenario: User exports memory
- **WHEN** the user clicks Export Memory and selects a destination path
- **THEN** `memory.json` is copied to that path and a success message is shown
