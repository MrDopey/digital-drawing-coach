## MODIFIED Requirements

### Requirement: LLM feedback uses art-coaching persona
The system SHALL include a system prompt that establishes the LLM as a knowledgeable digital art coach with expertise in perspective, anatomy, color theory, and technique. The persona SHALL remain consistent across all feedback modes. When a non-empty coach's notes block is provided (from the memory store), it SHALL be appended to the *end* of the system prompt, after the base persona, style fragment, custom instructions, and mode template, so that stable prefix is unaffected by per-session note changes and remains eligible for provider-side prompt caching. When the request uses the structured-output path, the observations schema field carries this data instead; when the request falls back to the prose path, the system prompt SHALL instruct the LLM to append a `<!-- observations: [...] -->` HTML comment containing a JSON array of `{category, note}` objects derived from the current response, to enable future memory accumulation.

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

#### Scenario: LLM instructed to emit observations comment on the prose fallback path
- **WHEN** a feedback request falls back to the prose path (structured output unsupported or failed)
- **THEN** the system prompt includes an instruction asking the LLM to append a `<!-- observations: [...] -->` comment with structured observations from its response

#### Scenario: No observations comment instruction on the structured path
- **WHEN** a feedback request uses the structured-output path
- **THEN** the system prompt does NOT instruct the LLM to append an observations comment, since observations are carried as a schema field instead

## ADDED Requirements

### Requirement: Feedback requests attempt structured JSON output once per application launch, then fall back for the rest of the session
The system SHALL maintain a process-lifetime flag (unset/`False` at application launch) tracking whether structured output has been found unavailable this run. While the flag is unset, the system SHALL attempt each feedback request via LiteLLM's structured-output mode, passing a JSON schema requiring a `feedback_text` string, an `observations` array of `{category, note}` objects, and (in `overlay` mode only) an `annotations` array matching the existing overlay annotation shape. If that attempt raises an error (e.g. the provider/model does not support `response_format` json-schema enforcement) or the returned content fails to parse or validate against the required fields, the system SHALL set the flag, fall back to the existing prose-plus-embedded-block prompt and regex-based extraction for that request so the user still receives a feedback response, and show the user a one-time warning (see the following requirement). Once the flag is set, every subsequent feedback request for the remainder of the application's run SHALL go directly to the prose path without attempting structured output again. The flag SHALL only be reset by restarting the application.

#### Scenario: Structured output succeeds
- **WHEN** a feedback request is made, the disable flag is unset, and the configured model returns a response conforming to the structured schema
- **THEN** the system uses the `feedback_text`, `observations`, and (if present) `annotations` fields directly, with no regex extraction performed, and the disable flag remains unset

#### Scenario: First structured attempt fails — flag set and this request still succeeds via fallback
- **WHEN** a feedback request is made, the disable flag is unset, and the structured-output attempt raises an error or returns content that fails validation
- **THEN** the system sets the disable flag, retries the same request using the prose prompt and regex-based extraction, and the user receives a normal feedback response for that request

#### Scenario: Subsequent requests skip structured output entirely
- **WHEN** a feedback request is made and the disable flag is already set (from an earlier failure this session)
- **THEN** the system goes directly to the prose prompt and regex-based extraction, without attempting the structured call

#### Scenario: Flag persists across the application's lifetime, reset only by restart
- **WHEN** the disable flag has been set at any point during the current application run
- **THEN** it remains set for every subsequent feedback request until the application is closed and relaunched

#### Scenario: Fallback path preserves existing error handling
- **WHEN** the prose fallback attempt itself fails (e.g. due to authentication, rate-limit, or network errors), whether on the request that first set the disable flag or any later request
- **THEN** the system surfaces the same error messages as today (see the "LLM errors are surfaced to the user" requirement)

### Requirement: User is warned once when structured output becomes unavailable
The first time the structured-output disable flag transitions from unset to set during an application run, the system SHALL show the user a one-time warning dialog stating that structured output is unavailable for this session, that memory notes and overlay annotations will rely on the less-reliable text-parsing fallback for the rest of the session, and that restarting the application will retry structured output. This warning SHALL NOT be shown again for the remainder of the run, regardless of how many further feedback requests are made.

#### Scenario: Warning shown on first disable
- **WHEN** the structured-output disable flag is set for the first time during an application run
- **THEN** the system shows a warning dialog explaining that structured output is unavailable this session, that memory/overlay features fall back to less-reliable text parsing, and that restarting will retry structured output

#### Scenario: Warning not repeated on later requests
- **WHEN** additional feedback requests are made after the disable flag was already set and the warning already shown
- **THEN** no further warning dialog is shown for the remainder of the application's run
