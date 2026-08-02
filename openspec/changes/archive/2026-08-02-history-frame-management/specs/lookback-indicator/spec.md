## ADDED Requirements

### Requirement: Visual lookback indicator on history panel thumbnails
The history panel SHALL visually distinguish the frames that will be sent to the LLM in the next feedback request. The indicated set is: the most recent frame plus up to `lookback_frames` prior frames (matching the selection logic in `FeedbackEngine`). Frames outside this window SHALL appear without the indicator. The indicator SHALL update automatically whenever the buffer changes (new capture added or frame deleted).

#### Scenario: Lookback frames are highlighted
- **WHEN** the history panel is open and the buffer contains frames
- **THEN** the thumbnails for the latest frame and up to `lookback_frames` prior frames each display a coloured border or badge to indicate they will be sent to the LLM

#### Scenario: Frames outside the lookback window are not highlighted
- **WHEN** the buffer contains more frames than `lookback_frames + 1`
- **THEN** the older frames beyond the lookback window do not show the indicator

#### Scenario: Indicator updates after a new capture
- **WHEN** a new frame is captured and added to the buffer while the history panel is open
- **THEN** the lookback indicator repositions to reflect the new latest frame and the updated window

#### Scenario: Indicator updates after a frame is deleted
- **WHEN** the user deletes a frame from the buffer via the history panel
- **THEN** the lookback indicator immediately updates to reflect the new buffer state and lookback window

#### Scenario: lookback_frames is zero
- **WHEN** `lookback_frames` is configured to 0
- **THEN** only the single most recent frame shows the indicator
