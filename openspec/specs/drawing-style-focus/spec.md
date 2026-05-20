# drawing-style-focus Specification

## Purpose
TBD - created by archiving change drawing-coach-enhancements. Update Purpose after archive.
## Requirements
### Requirement: User selects a drawing style from a preconfigured list
The system SHALL provide a style selector with the following preset options: Line Drawing, Realistic, Anime/Manga, Chibi, Concept Art, Portrait. The selected style SHALL be injected into every LLM system prompt for the duration of the session. The selection SHALL persist across sessions via the config file.

#### Scenario: User selects a preset style
- **WHEN** the user selects a style from the preset list (e.g. "Anime/Manga")
- **THEN** the system stores the selection and injects "The user is currently practising: Anime/Manga" into the LLM system prompt for all subsequent requests in this session

#### Scenario: No style is selected
- **WHEN** the user has not selected any style or focus
- **THEN** the system omits the style injection line from the system prompt and coaches in a general style

#### Scenario: Style persists across sessions
- **WHEN** the user reopens the application
- **THEN** the previously selected style is pre-populated in the selector

### Requirement: User enters a free-text focus description
The system SHALL allow the user to type a custom focus description (e.g. "gothic pokemon", "practising color theory", "foreshortening with dynamic poses"). This text SHALL be used instead of the preset style when non-empty, and SHALL also be injected into the LLM system prompt.

#### Scenario: User enters free-text focus
- **WHEN** the user types a custom focus string and confirms
- **THEN** the system stores it and injects "The user is currently focusing on: <custom text>" into the system prompt, replacing any preset style injection

#### Scenario: Free-text focus is cleared
- **WHEN** the user clears the free-text field and saves
- **THEN** the system reverts to the preset style selection (if any) or no injection

#### Scenario: Free-text is too long
- **WHEN** the user enters a focus description longer than 200 characters
- **THEN** the system SHALL truncate it to 200 characters and display a warning

### Requirement: Style/focus is visible in the main UI at all times
The system SHALL display the currently active style or focus as a label in the main application window so the user knows what coaching context is active.

#### Scenario: Active style shown in UI
- **WHEN** a style or focus is configured
- **THEN** the main window displays it as "Coaching for: <style or focus>" near the capture status indicator

#### Scenario: No style configured
- **WHEN** no style or focus is set
- **THEN** the main window displays "Coaching for: General" in the same location

