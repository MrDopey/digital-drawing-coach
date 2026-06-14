## ADDED Requirements

### Requirement: Feedback popup has a top control row
The Get Feedback popup SHALL display a top row containing the feedback type selector (mode combo) and the Generate Feedback button side by side. The Generate button SHALL reflect the disabled state described in the feedback-deduplication capability.

#### Scenario: Top row visible with controls
- **WHEN** the Get Feedback popup is open
- **THEN** the mode combo and Generate Feedback button are visible in the top row of the dialog

### Requirement: Left sidebar lists all feedback entries
The Get Feedback popup SHALL include a scrollable left sidebar listing all feedback entries for the current session in reverse-chronological order. Each row SHALL be labelled `DD Mon  HH:MM: <mode label>` (e.g. `14 Jun  09:41: Quick Look`). Clicking a row SHALL jump directly to that entry and display it in the main content area.

#### Scenario: Sidebar lists entries in reverse-chron order
- **WHEN** the feedback popup is open and history exists
- **THEN** the most recent entry appears at the top of the sidebar list

#### Scenario: Clicking a sidebar row shows that entry
- **WHEN** the user clicks a row in the sidebar
- **THEN** the main content area updates to show the thumbnail and feedback text for that entry

#### Scenario: New entry appears at top of sidebar after generation
- **WHEN** a new feedback response is generated
- **THEN** it is inserted at the top of the sidebar list and selected automatically

### Requirement: Main content area shows thumbnail and feedback text
The main content area of the Get Feedback popup SHALL display a small thumbnail preview of the last frame used for the selected feedback entry, followed by the feedback text (selectable, scrollable). Clicking the thumbnail SHALL open the image in the system default viewer using `QDesktopServices.openUrl` with a `file://` URL.

#### Scenario: Thumbnail displayed for selected entry
- **WHEN** a feedback entry is selected in the sidebar or via Prev/Next navigation
- **THEN** a thumbnail of the last frame used for that entry is shown in the main content area

#### Scenario: Clicking thumbnail opens image in default viewer
- **WHEN** the user clicks the thumbnail in the main content area
- **THEN** the system opens the corresponding image file in the system default image viewer

#### Scenario: Feedback text is selectable and scrollable
- **WHEN** a feedback entry is displayed
- **THEN** the feedback text can be selected with the mouse and scrolled if it exceeds the visible area

### Requirement: Previous and Next buttons navigate sequentially
The Get Feedback popup SHALL retain Previous and Next buttons for sequential navigation through feedback history, consistent with current behaviour.

#### Scenario: Next navigates to a newer entry
- **WHEN** the user clicks Next and a newer entry exists
- **THEN** the display advances to the next more-recent entry

#### Scenario: Previous navigates to an older entry
- **WHEN** the user clicks Previous and an older entry exists
- **THEN** the display moves to the next older entry
