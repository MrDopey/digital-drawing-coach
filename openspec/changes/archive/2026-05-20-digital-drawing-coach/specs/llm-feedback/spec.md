## ADDED Requirements

### Requirement: Send drawing screenshot to LLM for feedback
The system SHALL send the most recent screenshot (and up to 2 prior history frames when available) to the configured vision LLM and return structured drawing feedback. Images SHALL be encoded as base64 and sent via the LiteLLM `completion()` API.

#### Scenario: Feedback is triggered with a captured screenshot
- **WHEN** a feedback request is triggered (automatic or manual) and at least one screenshot is in the buffer
- **THEN** the system sends the screenshot(s) to the LLM and displays a loading indicator

#### Scenario: LLM returns a response
- **WHEN** the LLM responds successfully
- **THEN** the system renders the feedback in the feedback panel and dismisses the loading indicator

#### Scenario: No screenshots available when triggered
- **WHEN** a feedback request is triggered but the buffer is empty
- **THEN** the system SHALL display an error message "No drawing captured yet — please wait for the first screenshot"

### Requirement: LLM feedback uses art-coaching persona
The system SHALL include a system prompt that establishes the LLM as a knowledgeable digital art coach with expertise in perspective, anatomy, color theory, and technique. The persona SHALL remain consistent across all feedback modes.

#### Scenario: System prompt is sent with every request
- **WHEN** any feedback request is made
- **THEN** the art-coaching system prompt SHALL be prepended to the LiteLLM messages array

#### Scenario: User's custom instructions are respected
- **WHEN** the user has added custom coaching instructions in settings
- **THEN** those instructions SHALL be appended to the system prompt for every request

### Requirement: Feedback requests are rate-limited
The system SHALL reject or queue feedback requests that arrive within 10 seconds of the previous request to prevent duplicate LLM calls.

#### Scenario: Rapid successive triggers
- **WHEN** a feedback request is triggered within 10 seconds of the previous one completing
- **THEN** the system SHALL ignore the new trigger and display a "Please wait" message

### Requirement: LLM errors are surfaced to the user
The system SHALL display a clear, actionable error message when the LLM call fails, including the error type (auth failure, network error, model not found, etc.).

#### Scenario: API authentication fails
- **WHEN** the LLM returns an authentication error
- **THEN** the system displays "API key invalid or missing — check your LLM settings"

#### Scenario: Network is unavailable
- **WHEN** the LLM call fails due to a network error
- **THEN** the system displays "Network error — check your connection and try again"
