## MODIFIED Requirements

### Requirement: Left sidebar lists all feedback entries
The Feedback Management panel SHALL include a scrollable left sidebar (fixed width, adjustable via a splitter) listing all feedback entries for the current session — including entries persisted from before the app was last restarted — in reverse-chronological order. Each row SHALL be labelled `DD Mon  HH:MM: <mode label>` (e.g. `14 Jun  09:41: Quick Hint`). Rows SHALL be text only, with no per-entry image preview. Clicking a row SHALL jump directly to that entry, staying in sync with the existing Previous/Next navigation.

#### Scenario: Sidebar lists entries in reverse-chron order
- **WHEN** the feedback panel is open and history exists
- **THEN** the most recent entry appears at the top of the sidebar list

#### Scenario: Clicking a sidebar row shows that entry
- **WHEN** the user clicks a row in the sidebar
- **THEN** the main content area updates to show that entry's image and feedback text, and the Previous/Next buttons reflect the new position

#### Scenario: New entry appears at top of sidebar after generation
- **WHEN** a new feedback response is generated
- **THEN** it is inserted at the top of the sidebar list and selected automatically

#### Scenario: Sidebar reflects persisted history on open
- **WHEN** the feedback panel is opened and the active session has feedback entries saved from a previous run of the app
- **THEN** those entries appear in the sidebar without requiring a new feedback request

### Requirement: Main content area shows a mode-appropriate image preview and feedback text
The main content area SHALL display one image for the selected entry followed by the feedback text (selectable, scrollable). Every feedback mode SHALL use the same full-size, scrollable, zoomable image display described in the overlay-feedback spec — Overlay entries display their composited annotated image, and non-overlay entries (Quick Hint, Full Critique, Practice Exercise) display the full-resolution captured frame the feedback was based on. There SHALL be exactly one image display path: no downscaled thumbnail preview and no separate fixed-size image widget. When an entry has neither a composited overlay image nor a resolvable full-resolution frame, the image area SHALL be collapsed so the feedback text fills the available space.

#### Scenario: Non-overlay entry shows the full-resolution frame
- **WHEN** a Quick Hint, Full Critique, or Practice Exercise entry with a resolvable full-resolution frame is selected in the sidebar or via Previous/Next navigation
- **THEN** the main content area shows that frame in the full-size scrollable, zoomable image display

#### Scenario: Overlay entry shows the full annotated image
- **WHEN** an Overlay-mode entry is selected in the sidebar or via Previous/Next navigation
- **THEN** the main content area shows that entry's composited annotated image in the same full-size scrollable, zoomable image display

#### Scenario: Zoom controls apply to non-overlay entries
- **WHEN** the user activates a zoom control (or `Ctrl+Wheel` over the image) while a non-overlay entry's full-resolution frame is displayed
- **THEN** that image zooms exactly as an overlay image does

#### Scenario: Entry with no resolvable image shows no image
- **WHEN** an entry has no composited overlay image and its full-resolution frame is missing or was never recorded
- **THEN** the image area is collapsed, the feedback text fills the available space, and no error occurs

#### Scenario: Feedback text is selectable and scrollable
- **WHEN** a feedback entry is displayed
- **THEN** the feedback text can be selected with the mouse and scrolled if it exceeds the visible area
