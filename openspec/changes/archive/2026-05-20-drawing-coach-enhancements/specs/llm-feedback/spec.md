## MODIFIED Requirements

### Requirement: Send drawing screenshot to LLM for feedback
The system SHALL send the most recent screenshot and a configurable number of prior history frames (default: 2, range: 0–10, set in LLM settings) to the configured vision LLM and return structured drawing feedback. Images SHALL be encoded as base64 and sent via the LiteLLM `completion()` API.

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

### Requirement: LLM errors are surfaced to the user
The system SHALL display a clear, actionable error message when the LLM call fails or returns a policy refusal, covering all known error categories.

#### Scenario: API authentication fails
- **WHEN** the LLM returns an authentication error
- **THEN** the system displays "API key invalid or missing — check your LLM settings"

#### Scenario: Network is unavailable
- **WHEN** the LLM call fails due to a network error
- **THEN** the system displays "Network error — check your connection and try again"

#### Scenario: Rate limit is reached
- **WHEN** the LLM returns a rate-limit error
- **THEN** the system displays "Rate limit reached — wait a moment and try again" and does NOT auto-retry

#### Scenario: API credits are exhausted
- **WHEN** the LLM returns an insufficient-quota or budget-exceeded error
- **THEN** the system displays "Your API credits are exhausted — top up your account to continue"

#### Scenario: Model is not found
- **WHEN** the LLM returns a model-not-found error
- **THEN** the system displays "Model not found — check the model name in your LLM settings"

#### Scenario: LLM returns a content policy refusal
- **WHEN** the LLM response body contains a known policy-refusal phrase (e.g. "I'm unable to", "I cannot assist", "content policy")
- **THEN** the system displays "The LLM flagged a content policy issue with this image — try a different feedback mode or drawing" and does NOT treat it as a successful feedback response
