# llm-feedback Specification

## Purpose
TBD - created by archiving change digital-drawing-coach. Update Purpose after archive.
## Requirements
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

### Requirement: LLM feedback uses art-coaching persona
The system SHALL include a system prompt that establishes the LLM as a knowledgeable digital art coach with expertise in perspective, anatomy, color theory, and technique. The persona SHALL remain consistent across all feedback modes. When a non-empty coach's notes block is provided (from the memory store), it SHALL be appended to the *end* of the system prompt, after the base persona, style fragment, custom instructions, and mode template, so that stable prefix is unaffected by per-session note changes and remains eligible for provider-side prompt caching. The system prompt SHALL also instruct the LLM to optionally append a `<!-- observations: [...] -->` HTML comment containing a JSON array of `{category, note}` objects derived from the current response, to enable future memory accumulation.

#### Scenario: System prompt is sent with every request
- **WHEN** any feedback request is made
- **THEN** the art-coaching system prompt SHALL be prepended to the LiteLLM messages array

#### Scenario: User's custom instructions are respected
- **WHEN** the user has added custom coaching instructions in settings
- **THEN** those instructions SHALL be appended to the system prompt for every request

#### Scenario: Coach's notes block injected when memory is non-empty
- **WHEN** a feedback request is made and the memory store contains observations
- **THEN** the coach's notes block is appended to the end of the system prompt, after the base persona, style fragment, custom instructions, and mode template

#### Scenario: Coach's notes block omitted when memory is empty
- **WHEN** a feedback request is made and the memory store has no observations
- **THEN** the system prompt is assembled without a coach's notes block

#### Scenario: LLM instructed to emit observations comment
- **WHEN** any feedback request is made
- **THEN** the system prompt includes an instruction asking the LLM to append a `<!-- observations: [...] -->` comment with structured observations from its response

### Requirement: Feedback requests are rate-limited
The system SHALL reject or queue feedback requests that arrive within 10 seconds of the previous request to prevent duplicate LLM calls.

#### Scenario: Rapid successive triggers
- **WHEN** a feedback request is triggered within 10 seconds of the previous one completing
- **THEN** the system SHALL ignore the new trigger and display a "Please wait" message

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

