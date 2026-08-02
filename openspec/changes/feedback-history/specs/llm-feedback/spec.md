## MODIFIED Requirements

### Requirement: Send drawing screenshot to LLM for feedback
The system SHALL send the most recent screenshot and a configurable number of prior history frames (default: 2, range: 0–10, set in LLM settings) to the configured vision LLM and return structured drawing feedback. Images SHALL be encoded as base64 and sent via the LiteLLM `completion()` API. When the feedback mode is `overlay`, the system SHALL send only the single most recent screenshot, ignoring the configured look-back count, so that annotation coordinates returned by the LLM are unambiguously relative to the one image the app will render them onto. `FeedbackEngine` SHALL compute a `frame_hashes` field — the SHA-256 hex digest of each frame's image data actually sent, in the same order as the frames sent — locally from the `CapturedFrame` data already in memory, and attach it to the `FeedbackResponse` it returns. This computation SHALL NOT involve the LLM in any way: it is not sent to the model, not part of `_STRUCTURED_RESPONSE_SCHEMA`, and not something the model is asked to produce or echo back. It happens identically regardless of whether the request used the structured-JSON-output path or the prose-parsing fallback, since both paths select their frames the same way before dispatching.

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

#### Scenario: FeedbackResponse includes frame hashes
- **WHEN** a successful LLM response is returned, whether via the structured-JSON-output path or the prose-parsing fallback
- **THEN** the `FeedbackResponse.frame_hashes` list contains one SHA-256 hex string per frame that was sent, in send order

#### Scenario: Overlay mode frame hashes contain exactly one entry
- **WHEN** a successful LLM response is returned for mode `overlay`
- **THEN** the `FeedbackResponse.frame_hashes` list contains exactly one SHA-256 hex string, matching the single screenshot sent
