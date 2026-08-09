## ADDED Requirements

### Requirement: Hover tracking receives mouse events from the whole row

Row hover detection SHALL receive mouse-move events for every point within a row, including points covered by the row's thumbnail and timestamp widgets.

Because hover is tracked by an event filter on the list viewport, and a `setItemWidget()` row covers that viewport completely, the row widget and its non-interactive children SHALL be transparent to mouse events so hit-testing falls through to the viewport. Interactive children — the delete button — SHALL remain able to receive mouse events.

The highlight SHALL follow the cursor without perceptible delay. It SHALL NOT depend on the cursor crossing the row's layout margins or any other region not covered by a child widget.

#### Scenario: Cursor moves over a row's label area
- **WHEN** the mouse cursor moves over the part of a history row occupied by its thumbnail or timestamp label
- **THEN** the hover tracker SHALL receive that move and the row SHALL show the hover highlight

#### Scenario: Row widget does not intercept mouse events
- **WHEN** the history panel builds a row
- **THEN** the row widget and its thumbnail and timestamp labels SHALL be transparent to mouse events

#### Scenario: Delete button remains interactive
- **WHEN** the row widget is transparent to mouse events
- **THEN** the row's delete button SHALL still receive mouse events and remain clickable

#### Scenario: Hit-testing finds no child at a row's centre
- **WHEN** the list viewport is hit-tested at the centre point of a row
- **THEN** no child widget SHALL be returned, so the event is delivered to the viewport where the hover filter is installed
