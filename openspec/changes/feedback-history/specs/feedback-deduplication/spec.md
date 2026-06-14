## ADDED Requirements

### Requirement: Generate button disabled for already-submitted image+mode combinations
The system SHALL disable the **Generate Feedback** button when the current set of frame hashes and selected feedback mode exactly matches those of the most recent saved feedback entry for that mode. The button SHALL display a tooltip explaining why it is disabled. The button SHALL be re-enabled when a new frame is captured that was not part of the previous request, or when the user switches to a feedback mode that has not been run against the current images.

#### Scenario: Same images and mode already submitted
- **WHEN** the current frame buffer hashes and selected mode match the last saved entry for that mode
- **THEN** the Generate Feedback button is disabled with a tooltip such as "Already generated for this drawing and mode"

#### Scenario: New frame captured re-enables button
- **WHEN** a new frame is captured and added to the buffer after a submission
- **THEN** the Generate Feedback button is re-enabled

#### Scenario: Mode change re-enables button
- **WHEN** the user switches to a feedback mode that has not been run against the current frame set
- **THEN** the Generate Feedback button is re-enabled

#### Scenario: No prior history — button enabled
- **WHEN** no feedback has been generated yet for the current session
- **THEN** the Generate Feedback button is enabled
