# feedback-panel-redesign Specification

## Purpose
TBD - created by archiving change feedback-history. Update Purpose after archive.

## Requirements
### Requirement: Left sidebar lists all feedback entries
The Feedback Management panel SHALL include a scrollable left sidebar (fixed width, adjustable via a splitter) listing all feedback entries for the current session — including entries persisted from before the app was last restarted — in reverse-chronological order. Each row SHALL be labelled `DD Mon  HH:MM: <mode label>` (e.g. `14 Jun  09:41: Quick Hint`). Clicking a row SHALL jump directly to that entry, staying in sync with the existing Previous/Next navigation.

#### Scenario: Sidebar lists entries in reverse-chron order
- **WHEN** the feedback panel is open and history exists
- **THEN** the most recent entry appears at the top of the sidebar list

#### Scenario: Clicking a sidebar row shows that entry
- **WHEN** the user clicks a row in the sidebar
- **THEN** the main content area updates to show that entry's image (thumbnail or overlay, per mode) and feedback text, and the Previous/Next buttons reflect the new position

#### Scenario: New entry appears at top of sidebar after generation
- **WHEN** a new feedback response is generated
- **THEN** it is inserted at the top of the sidebar list and selected automatically

#### Scenario: Sidebar reflects persisted history on open
- **WHEN** the feedback panel is opened and the active session has feedback entries saved from a previous run of the app
- **THEN** those entries appear in the sidebar without requiring a new feedback request

### Requirement: Main content area shows a mode-appropriate image preview and feedback text
For non-overlay entries (Quick Hint, Full Critique, Practice Exercise), the main content area SHALL display a small thumbnail preview of the last frame used, followed by the feedback text (selectable, scrollable). Clicking the thumbnail SHALL open the image in the system default viewer using `QDesktopServices.openUrl` with a `file://` URL. Overlay-mode entries SHALL instead continue to use the existing full-size zoomable/pannable annotated image display, per the overlay-feedback spec — the small thumbnail applies only to modes that currently have no image display of their own.

#### Scenario: Thumbnail displayed for a non-overlay entry
- **WHEN** a Quick Hint, Full Critique, or Practice Exercise entry is selected in the sidebar or via Previous/Next navigation
- **THEN** a thumbnail of the last frame used for that entry is shown in the main content area

#### Scenario: Overlay entry shows the full annotated image, not a thumbnail
- **WHEN** an Overlay-mode entry is selected in the sidebar or via Previous/Next navigation
- **THEN** the main content area shows the existing zoomable/pannable annotated image for that entry, not the small thumbnail

#### Scenario: Clicking thumbnail opens image in default viewer
- **WHEN** the user clicks the thumbnail in the main content area
- **THEN** the system opens the corresponding image file in the system default image viewer

#### Scenario: Feedback text is selectable and scrollable
- **WHEN** a feedback entry is displayed
- **THEN** the feedback text can be selected with the mouse and scrolled if it exceeds the visible area

### Requirement: Previous and Next buttons navigate sequentially
The Feedback Management panel SHALL retain Previous and Next buttons for sequential navigation through feedback history, consistent with current behaviour, and SHALL keep the sidebar selection synchronized with whichever entry Previous/Next navigates to.

#### Scenario: Next navigates to a newer entry
- **WHEN** the user clicks Next and a newer entry exists
- **THEN** the display advances to the next more-recent entry and the sidebar selection updates to match

#### Scenario: Previous navigates to an older entry
- **WHEN** the user clicks Previous and an older entry exists
- **THEN** the display moves to the next older entry and the sidebar selection updates to match
