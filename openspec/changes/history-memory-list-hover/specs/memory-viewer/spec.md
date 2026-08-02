## ADDED Requirements

### Requirement: Observation row background highlight on hover
Each observation row in the memory viewer's tree SHALL highlight its background when the mouse cursor is over that row, consistent with the row hover-highlight behavior of the Session History panel.

#### Scenario: Mouse enters an observation row
- **WHEN** the mouse cursor enters an observation row's area in the memory viewer
- **THEN** that row's background SHALL change to a distinct highlight color

#### Scenario: Mouse leaves an observation row
- **WHEN** the mouse cursor leaves an observation row's area
- **THEN** that row's background SHALL return to its normal (non-highlighted) color

#### Scenario: Category header rows are unaffected
- **WHEN** the mouse cursor moves over a top-level category header row (not an individual observation)
- **THEN** no observation-row hover highlight is required for that header row
