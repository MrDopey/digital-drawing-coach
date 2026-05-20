# app-selection Specification

## Purpose
TBD - created by archiving change digital-drawing-coach. Update Purpose after archive.
## Requirements
### Requirement: User selects target drawing application
The system SHALL allow the user to select the drawing application window to monitor from a list of currently open windows. The selected window SHALL be persisted within the session so the user does not need to reselect after the app restarts capture.

#### Scenario: User opens app selection
- **WHEN** the user opens the app for the first time or clicks "Change Window"
- **THEN** the system displays a list of currently open application windows with their names and thumbnails

#### Scenario: User selects a window
- **WHEN** the user selects a window from the list
- **THEN** the system stores that window as the capture target and shows a confirmation with the window name

#### Scenario: Selected window is closed
- **WHEN** the monitored drawing application window is closed or becomes unavailable
- **THEN** the system SHALL pause capture, display a warning, and prompt the user to reselect a window

#### Scenario: No drawing application is open
- **WHEN** the user opens app selection but no windows are available
- **THEN** the system SHALL display an empty state message instructing the user to open their drawing application first

### Requirement: Window list refreshes on demand
The system SHALL provide a refresh mechanism to update the list of available windows without restarting the application.

#### Scenario: User refreshes window list
- **WHEN** the user clicks "Refresh" in the app selection dialog
- **THEN** the system re-enumerates open windows and updates the list within 2 seconds

