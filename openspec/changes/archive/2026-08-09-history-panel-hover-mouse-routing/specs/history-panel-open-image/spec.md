## ADDED Requirements

### Requirement: Double-click activation is independent of row-widget mouse handling

Double-click activation of a history row SHALL be handled by the list view's item-activation signal rather than by a mouse event handler on the row widget, so that it continues to work while the row widget is transparent to mouse events for hover tracking.

#### Scenario: Double-click while the row is mouse-transparent
- **WHEN** the user double-clicks a row whose widget is transparent to mouse events
- **THEN** the system SHALL resolve the frame from the activated list item and open its image, exactly as before

#### Scenario: Double-click is delivered through the list viewport
- **WHEN** a double-click is delivered to the list viewport at a row's position
- **THEN** the system SHALL open that row's frame, without relying on the row widget receiving the event itself
