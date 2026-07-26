# progress-panel Specification

## Purpose
TBD - created by change long-term-memory. Update Purpose after archive.

## Requirements
### Requirement: Progress panel shows recurring themes from memory
The system SHALL provide a progress panel (tab or dialog) accessible from the main window that summarises recurring themes from the memory store. Each category SHALL be shown with its observation count and the number of distinct sessions in which it appeared (e.g. "Perspective: 7 observations across 4 sessions").

#### Scenario: Progress panel with observations
- **WHEN** the user opens the progress panel and observations exist
- **THEN** each category is listed with its observation count and distinct session count

#### Scenario: Progress panel with no observations
- **WHEN** the user opens the progress panel and no observations exist
- **THEN** the panel shows an empty state message (e.g. "No progress data yet — start drawing and getting feedback!")

### Requirement: Progress panel shows session practice timeline
The progress panel SHALL display a simple timeline listing the start dates of past sessions (loaded from `meta.json` files in `sessions_dir()`) so the user can see how often they practise.

#### Scenario: Session timeline shown
- **WHEN** the user opens the progress panel
- **THEN** a list of past session start dates (formatted as `DD Mon YYYY, HH:MM`) is displayed in reverse-chronological order

#### Scenario: No sessions recorded
- **WHEN** no session directories exist on disk
- **THEN** the timeline shows an empty state message
