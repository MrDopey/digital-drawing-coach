## ADDED Requirements

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
