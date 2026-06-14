## ADDED Requirements

### Requirement: Config load is logged at INFO
The system SHALL emit an INFO log when LLM configuration is loaded, stating the resolved config file path.

#### Scenario: Config loaded from disk
- **WHEN** `LLMConfig.load()` reads an existing config file
- **THEN** an INFO log is emitted: `Config loaded from <absolute_path>`

#### Scenario: Config file not found, defaults used
- **WHEN** `LLMConfig.load()` finds no config file
- **THEN** an INFO log is emitted: `No config file found, using defaults`

### Requirement: API key presence is logged at INFO/WARNING
The system SHALL emit an INFO log if an API key is found in the environment, or a WARNING if no key is configured, so users can confirm key injection without exposing the key value.

#### Scenario: API key is present
- **WHEN** `LLMConfig.load()` resolves an API key (from env or `.env` file)
- **THEN** an INFO log is emitted: `API key present`

#### Scenario: API key is absent
- **WHEN** `LLMConfig.load()` finds no API key
- **THEN** a WARNING log is emitted: `No API key configured — LLM calls will fail unless using a local model`

### Requirement: LLM call lifecycle is logged
The system SHALL emit logs at the start and end of every LLM API call, including model name, feedback mode, and outcome.

#### Scenario: LLM call initiated
- **WHEN** `FeedbackEngine.request_feedback()` sends a request to the LLM
- **THEN** an INFO log is emitted: `LLM request: model=<model> mode=<mode> frames=<N>`

#### Scenario: LLM call succeeds
- **WHEN** the LLM returns a response
- **THEN** an INFO log is emitted: `LLM response received in <elapsed_ms>ms`

#### Scenario: LLM call fails with an error
- **WHEN** the LLM call raises an exception
- **THEN** an ERROR log is emitted: `LLM call failed: <error_message>`

#### Scenario: Rate limit is hit
- **WHEN** `FeedbackEngine` suppresses a call due to the rate-limit window
- **THEN** a WARNING log is emitted: `Rate limit: <N>s remaining before next request`

#### Scenario: LLM returns a policy refusal
- **WHEN** the LLM response contains a recognised policy-refusal phrase
- **THEN** a WARNING log is emitted: `LLM policy refusal detected`
