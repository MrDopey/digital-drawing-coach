## Requirements

### Requirement: Open thumbnail in default image viewer on double-click
The history panel SHALL open the full-resolution image for a thumbnail in the system's default application for PNG files when the user double-clicks that thumbnail.

#### Scenario: Double-click disk-backed frame
- **WHEN** the user double-clicks a thumbnail whose `CapturedFrame.path` is a valid file path
- **THEN** the system SHALL open that file using the OS default PNG viewer via `QDesktopServices.openUrl`

#### Scenario: Double-click in-memory frame
- **WHEN** the user double-clicks a thumbnail whose `CapturedFrame.path` is `None`
- **THEN** the system SHALL save the frame's PIL image to a temporary PNG file and open it using `QDesktopServices.openUrl`

#### Scenario: No default viewer registered
- **WHEN** `QDesktopServices.openUrl` returns `False` (no handler registered)
- **THEN** the system SHALL display a warning dialog informing the user that no default viewer is configured

### Requirement: Discoverable affordance
The history panel SHALL display a hint label indicating that thumbnails can be double-clicked to open them, so the interaction is discoverable without prior knowledge.

#### Scenario: Hint visible when frames are present
- **WHEN** the history panel is opened and one or more frames are displayed
- **THEN** a status label reading "Double-click a thumbnail to open it" (or equivalent) SHALL be visible in the panel

### Requirement: List layout sorted newest-first
The history panel SHALL display frames as a vertical list (not an icon grid), with the most recently captured frame at the top.

#### Scenario: Frames shown in reverse chronological order
- **WHEN** the history panel is opened with two or more captured frames
- **THEN** the frame with the latest timestamp SHALL appear first in the list and frames SHALL be ordered descending by capture time

#### Scenario: List view with thumbnail and timestamp
- **WHEN** a frame is displayed in the list
- **THEN** each row SHALL show a small thumbnail icon alongside the capture timestamp as text

### Requirement: Double-click activation is independent of row-widget mouse handling
Double-click activation of a history row SHALL be handled by the list view's item-activation signal rather than by a mouse event handler on the row widget, so that it continues to work while the row widget is transparent to mouse events for hover tracking.

#### Scenario: Double-click while the row is mouse-transparent
- **WHEN** the user double-clicks a row whose widget is transparent to mouse events
- **THEN** the system SHALL resolve the frame from the activated list item and open its image, exactly as before

#### Scenario: Double-click is delivered through the list viewport
- **WHEN** a double-click is delivered to the list viewport at a row's position
- **THEN** the system SHALL open that row's frame, without relying on the row widget receiving the event itself
