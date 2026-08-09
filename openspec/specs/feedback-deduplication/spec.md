# feedback-deduplication Specification

## Purpose
TBD - created by archiving change feedback-history. Update Purpose after archive.

## Requirements
### Requirement: Request Feedback button disabled for already-submitted image+mode combinations
The system SHALL disable the **Request Feedback** button when the current set of frame hashes and selected feedback mode exactly matches those of the most recent saved feedback entry for that mode. The button SHALL display a tooltip explaining why it is disabled. The button SHALL be re-enabled when a new frame is captured that was not part of the previous request, or when the user switches to a feedback mode that has not been run against the current images.

A saved entry SHALL take part in this match only when its frame hashes are known — either recorded in its JSON or derived from its frame image on disk. An entry whose frame hashes cannot be established SHALL NOT match any current frame set, including an empty one. Likewise, when the current frame set is empty there is nothing to de-duplicate against, and the button SHALL remain enabled regardless of saved history.

#### Scenario: Same images and mode already submitted
- **WHEN** the current frame buffer hashes and selected mode match the last saved entry for that mode
- **THEN** the Request Feedback button is disabled with a tooltip such as "Already generated for this drawing and mode"

#### Scenario: New frame captured re-enables button
- **WHEN** a new frame is captured and added to the buffer after a submission
- **THEN** the Request Feedback button is re-enabled

#### Scenario: Mode change re-enables button
- **WHEN** the user switches to a feedback mode that has not been run against the current frame set
- **THEN** the Request Feedback button is re-enabled

#### Scenario: No prior history — button enabled
- **WHEN** no feedback has been generated yet for the current session
- **THEN** the Request Feedback button is enabled

#### Scenario: Entry with unknown frame hashes never suppresses the button
- **WHEN** the session's history contains an entry for the selected mode whose frame hashes are neither recorded in its JSON nor recoverable from disk
- **THEN** that entry is skipped when matching, and the Request Feedback button is enabled

#### Scenario: No frames captured yet — button enabled
- **WHEN** the capture buffer is empty, so the current frame set is empty, and the session's history contains entries for the selected mode
- **THEN** the Request Feedback button is enabled

#### Scenario: Backfilled entry still de-duplicates
- **WHEN** an entry whose frame hashes were derived from its frame image on disk is the last entry for the selected mode, and the current frame set hashes to the same values
- **THEN** the Request Feedback button is disabled, exactly as for an entry with recorded hashes
