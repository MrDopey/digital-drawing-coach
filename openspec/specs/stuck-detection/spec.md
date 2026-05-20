# stuck-detection Specification

## Purpose
TBD - created by archiving change digital-drawing-coach. Update Purpose after archive.
## Requirements
### Requirement: Automatic stuck detection via pixel change heuristic
The system SHALL compare consecutive captured frames using mean absolute pixel difference (MAE). If MAE falls below a configurable threshold for a configurable number of consecutive intervals, the system SHALL classify the user as "stuck" and trigger a feedback request. All three parameters (MAE threshold, consecutive interval count, and cooldown duration) SHALL be configurable via the settings panel and persisted in the config file.

#### Scenario: User has not drawn for several intervals
- **WHEN** MAE between the last N consecutive frame pairs is below the configured threshold
- **THEN** the system marks the session as "stuck" and triggers an automatic feedback request

#### Scenario: User resumes drawing after being stuck
- **WHEN** MAE rises above the threshold after a stuck state
- **THEN** the system clears the stuck flag and does not trigger another automatic feedback request until the next stuck period

#### Scenario: Stuck threshold is adjusted by user
- **WHEN** the user changes the pixel-change threshold in settings
- **THEN** the system applies the new threshold to future comparisons without resetting the session

#### Scenario: Consecutive interval count is adjusted by user
- **WHEN** the user changes the consecutive interval count in settings (default: 3, range: 1–20)
- **THEN** the system applies the new count to future stuck-detection evaluations without resetting the session

#### Scenario: All stuck-detection parameters shown in settings
- **WHEN** the user opens the settings panel
- **THEN** the Stuck Detection section displays three configurable fields: MAE Threshold, Consecutive Intervals, and Cooldown Duration, each with its current value and default shown

### Requirement: Manual stuck trigger via hotkey
The system SHALL allow the user to trigger a feedback request at any time using a configurable global hotkey, regardless of the automatic detection state.

#### Scenario: User presses the feedback hotkey
- **WHEN** the user presses the configured global hotkey while the drawing app is in focus
- **THEN** the system immediately queues a feedback request using the current screenshot and recent history

#### Scenario: Hotkey conflicts with drawing app shortcut
- **WHEN** the configured hotkey is the same as a known shortcut in the selected drawing application
- **THEN** the system SHALL warn the user in settings and suggest an alternative

#### Scenario: Hotkey is reconfigured
- **WHEN** the user saves a new hotkey in settings
- **THEN** the system unregisters the old hotkey and registers the new one within 1 second without restarting

### Requirement: Cooldown between automatic triggers
The system SHALL enforce a configurable minimum cooldown between automatic stuck-detection triggers to prevent feedback spam. The cooldown duration SHALL be configurable via the settings panel (default: 5 minutes, range: 1–60 minutes) and persisted in the config file.

#### Scenario: Cooldown is active
- **WHEN** the system triggered automatic feedback and the cooldown period has not elapsed
- **THEN** the system SHALL NOT trigger another automatic feedback request even if stuck is re-detected

#### Scenario: Manual trigger bypasses cooldown
- **WHEN** the user presses the manual hotkey during an active cooldown
- **THEN** the system SHALL still trigger feedback immediately and reset the cooldown timer

#### Scenario: Cooldown duration is changed by user
- **WHEN** the user updates the cooldown duration in settings and saves
- **THEN** the new duration takes effect for the next cooldown period; any currently active cooldown continues with the old duration

