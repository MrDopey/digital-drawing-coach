# llm-debug-logging Specification

## Purpose
Defines settings-gated debug logging of raw LLM request/response data for every `litellm.completion()` call the application makes, so LLM behaviour (feedback requests, connectivity checks, and memory re-summarisation) can be diagnosed from disk artifacts without adding an in-app viewer. Off by default; never persists request/response data unless explicitly enabled, and never breaks the calling feature if writing fails.

## Requirements

### Requirement: Debug logging of LLM input/output is settings-gated and off by default
The system SHALL provide a "Debug logging of LLM input/output" checkbox in the Settings dialog's LLM tab, persisted as `LLMConfig.debug_log_llm_io` (default `False`). No request or response data SHALL be persisted to disk for any LLM call unless this setting is enabled.

#### Scenario: Setting is off by default
- **WHEN** a fresh install or existing config has no `debug_log_llm_io` value stored
- **THEN** `LLMConfig.debug_log_llm_io` defaults to `False` and no debug artifacts are written for any LLM call

#### Scenario: User enables the setting
- **WHEN** the user checks "Debug logging of LLM input/output" in Settings → LLM and clicks Save
- **THEN** the setting is persisted to the config file and subsequent LLM calls write debug artifacts to disk

#### Scenario: User disables the setting
- **WHEN** the user unchecks "Debug logging of LLM input/output" and clicks Save
- **THEN** subsequent LLM calls write no debug artifacts, and previously written artifacts are left untouched

### Requirement: Enabled debug logging covers every LLM call the application makes
When `debug_log_llm_io` is enabled, the system SHALL persist the request and response (or error) of every `litellm.completion()` call the application makes — not only feedback requests — to a per-call directory under `debug_log_dir()`. This SHALL include: `FeedbackEngine`'s structured-output attempt and its prose fallback (all feedback modes), the Diagnostics dialog's LLM connectivity check, the Settings dialog's "Test Connection" action, and `MemoryStore`'s periodic coach's-notes re-summarisation call.

#### Scenario: Feedback request completes successfully
- **WHEN** a feedback request is made with debug logging enabled and the LLM returns a response
- **THEN** the system writes one PNG file per image actually sent to the LLM (in the same order and content as the request payload), a text file with the request's text content, and a text file containing the complete, unmodified raw response text, into a new timestamped subdirectory of `debug_log_dir()`

#### Scenario: Overlay mode logs only the single frame actually sent
- **WHEN** a feedback request in `overlay` mode is made with debug logging enabled
- **THEN** exactly one image file is written, matching the single latest frame the LLM was shown — not any additional look-back frames

#### Scenario: Non-overlay mode logs all frames actually sent
- **WHEN** a feedback request in `quick_hint`, `full_critique`, or `practice_exercise` mode is made with debug logging enabled and look-back frames are configured
- **THEN** one image file is written per frame actually included in the request (latest plus look-back frames), matching what was sent to the LLM

#### Scenario: Raw response includes embedded JSON and observations comment
- **WHEN** debug logging is enabled and the LLM response contains an annotation JSON block and/or an `<!-- observations: ... -->` comment
- **THEN** the persisted response text file contains that content verbatim, unmodified by any later JSON-extraction or stripping performed on the in-memory response

#### Scenario: Feedback policy refusal or LLM error is still logged
- **WHEN** debug logging is enabled and a feedback request is detected as a content-policy refusal, or the underlying LLM call raises an authentication, rate-limit, not-found, or other error
- **THEN** the sent image(s)/text and the raw response text or error detail are still persisted, since a failure is itself useful diagnostic information

#### Scenario: Structured-output attempt and prose fallback are logged as distinct, attributable calls
- **WHEN** debug logging is enabled, a feedback request's structured-output attempt fails, and `FeedbackEngine` falls back to the prose path for that request
- **THEN** two separate debug-log entries are written — one for the failed structured attempt (with an `error.txt`) and one for the successful prose fallback (with a `response.txt`) — each identifiable by its debug label as belonging to the structured or prose path respectively

#### Scenario: Diagnostics LLM connectivity check is logged
- **WHEN** debug logging is enabled and the user runs the Diagnostics dialog's LLM connectivity check
- **THEN** the request text and the raw response (or error, if the check fails) are persisted to a timestamped subdirectory of `debug_log_dir()`

#### Scenario: Settings "Test Connection" is logged
- **WHEN** debug logging is enabled and the user clicks "Test Connection" in Settings → LLM
- **THEN** the request text and the raw response (or error, if the connection test fails) are persisted to a timestamped subdirectory of `debug_log_dir()`

#### Scenario: Memory re-summarisation call is logged
- **WHEN** debug logging is enabled and `MemoryStore` performs a periodic re-summarisation LLM call
- **THEN** the request text (prior summary and new observations) and the raw response (or error, if re-summarisation fails) are persisted to a timestamped subdirectory of `debug_log_dir()`

### Requirement: Debug logging failures never break the calling feature
Errors while writing debug artifacts SHALL be caught, logged at WARNING, and SHALL NOT prevent any LLM call site's normal return value or control flow.

#### Scenario: Debug log directory cannot be created or written
- **WHEN** debug logging is enabled but `debug_log_dir()` cannot be created or is not writable
- **THEN** the system logs a WARNING describing the failure, and the calling feature (feedback request, diagnostics check, test connection, or re-summarisation) proceeds and returns its normal result unaffected

### Requirement: Debug log location is documented
The system SHALL document the resolved debug log directory path in the README, since there is no in-app UI to browse captured debug artifacts.

#### Scenario: User wants to find captured debug artifacts
- **WHEN** a user has enabled debug logging and wants to locate the captured files
- **THEN** the README describes the debug log directory location (sibling to the sessions directory), its per-call subdirectory naming, and that it covers all LLM calls the app makes, not just feedback requests
