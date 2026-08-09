# history-panel-theming Specification

## Purpose
TBD - created by syncing change session-history-redesign. Update Purpose after archive.

## Requirements
### Requirement: Delete button matches app button styling
Each history row's delete button SHALL be styled consistently with the rest of the app's buttons (rounded corners, themed background, and a visually distinct hover state) instead of rendering as a bare unstyled square button.

#### Scenario: Delete button visible on row hover
- **WHEN** the mouse enters a history row and the delete button becomes visible
- **THEN** the delete button SHALL render with rounded corners and the app's themed button background color

#### Scenario: Delete button hovered directly
- **WHEN** the mouse is over the delete button itself
- **THEN** the delete button SHALL render its hover background color, matching the hover behavior of other buttons in the app

### Requirement: Row background highlight on hover
Each history row SHALL highlight its background when the mouse cursor is over that row, independent of and simultaneous with the existing delete-button-reveal and lookback-window border indicator.

#### Scenario: Mouse enters a row
- **WHEN** the mouse cursor enters a history row's area
- **THEN** that row's background SHALL change to a distinct highlight color

#### Scenario: Mouse leaves a row
- **WHEN** the mouse cursor leaves a history row's area
- **THEN** that row's background SHALL return to its normal (non-highlighted) color

#### Scenario: Hover highlight combined with lookback-window border
- **WHEN** the mouse cursor enters a row that is also within the LLM's current lookback window (already marked with the left-border indicator)
- **THEN** the row SHALL show both the hover background highlight and the lookback left-border indicator at the same time, without either one overriding the other

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
