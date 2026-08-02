## MODIFIED Requirements

### Requirement: Send drawing screenshot to LLM for feedback
The system SHALL send the most recent screenshot and a configurable number of prior history frames (default: 2, range: 0–10, set in LLM settings) to the configured vision LLM and return structured drawing feedback. Images SHALL be encoded as base64 and sent via the LiteLLM `completion()` API. When the feedback mode is `overlay`, the system SHALL send only the single most recent screenshot, ignoring the configured look-back count, so that annotation coordinates returned by the LLM are unambiguously relative to the one image the app will render them onto.

#### Scenario: Feedback is triggered with a captured screenshot
- **WHEN** a feedback request is triggered (automatic or manual) and at least one screenshot is in the buffer
- **THEN** the system sends the screenshot(s) to the LLM and displays a loading indicator

#### Scenario: LLM returns a response
- **WHEN** the LLM responds successfully
- **THEN** the system renders the feedback in the feedback panel and dismisses the loading indicator

#### Scenario: No screenshots available when triggered
- **WHEN** a feedback request is triggered but the buffer is empty
- **THEN** the system SHALL display an error message "No drawing captured yet — please wait for the first screenshot"

#### Scenario: Look-back count is set to zero
- **WHEN** the look-back frame count is configured to 0
- **THEN** the system sends only the most recent screenshot with no history frames

#### Scenario: Look-back count exceeds available history
- **WHEN** the look-back count is greater than the number of stored frames
- **THEN** the system sends all available frames without error

#### Scenario: Overlay mode ignores the configured look-back count
- **WHEN** a feedback request is triggered with mode `overlay` and the configured look-back count is greater than 0
- **THEN** the system sends only the single most recent screenshot to the LLM, not any prior history frames
