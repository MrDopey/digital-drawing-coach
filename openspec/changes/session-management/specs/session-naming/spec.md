## ADDED Requirements

### Requirement: Sessions have a user-editable name
Each session SHALL have a human-readable name stored as `name` in `meta.json`. When no name has been set the system SHALL derive a default from the session start time (e.g. `Session 14 Jun 2026, 09:41`). The name SHALL be editable inline in the session picker (double-click or pencil icon) and from the main window (header or settings area).

#### Scenario: New session gets a default name
- **WHEN** a new session is created
- **THEN** `meta.json` contains a `name` field set to a timestamp-derived label (e.g. `Session 14 Jun 2026, 09:41`)

#### Scenario: Existing session without name field falls back to timestamp label
- **WHEN** an existing session's `meta.json` has no `name` field
- **THEN** the system displays the timestamp-derived label in all UI locations where the name would appear

#### Scenario: User renames a session in the picker
- **WHEN** the user double-clicks a session name (or clicks its pencil icon) in the picker and types a new name
- **THEN** the new name is saved to `meta.json` immediately and the picker row updates to show the new name

#### Scenario: User renames the active session from the main window
- **WHEN** the user edits the session name in the main window's header or settings area and confirms
- **THEN** the new name is saved to `meta.json` and the title bar updates to reflect the new name

#### Scenario: Name is empty after edit
- **WHEN** the user clears the name field and confirms
- **THEN** the system restores the default timestamp-derived label (does not save an empty string)
