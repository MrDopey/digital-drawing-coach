## MODIFIED Requirements

### Requirement: Periodic screenshot capture
The system SHALL capture a screenshot of the selected drawing window at a user-configurable interval (default: 30 seconds, range: 5–300 seconds). A captured frame SHALL contain only the selected window's own content — not other on-screen windows, overlays, or desktop area — even when other windows visually overlap or obscure it on screen. Captures SHALL be stored to disk under a per-session directory (`~/.drawing-coach/sessions/<session-id>/frames/`). Near-duplicate frames SHALL be dropped before writing using a configurable MAE deduplication threshold (default: 2.0, independently configurable from the stuck-detection threshold).

#### Scenario: Capture runs on schedule
- **WHEN** a drawing window is selected and capture is active
- **THEN** the system captures a screenshot of that window at each interval tick

#### Scenario: Another window overlaps the selected window
- **WHEN** another application's window is positioned on top of part of the selected drawing window on screen
- **THEN** the captured frame shows only the selected window's own content in that area, not the overlapping window's content

#### Scenario: Duplicate frame is detected and dropped
- **WHEN** a newly captured frame has MAE below the deduplication threshold compared to the last stored frame
- **THEN** the system discards the new frame without writing to disk and without updating the session history view

#### Scenario: Non-duplicate frame is stored
- **WHEN** a newly captured frame has MAE above the deduplication threshold
- **THEN** the system writes the frame to disk as a PNG with a timestamp filename and adds it to the session history view

#### Scenario: Capture interval changed by user
- **WHEN** the user updates the capture interval in settings
- **THEN** the system applies the new interval on the next tick without restarting the session
