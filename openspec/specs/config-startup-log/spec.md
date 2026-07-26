# config-startup-log Specification

## Purpose
Defines how the application logs its active configuration at startup so that configuration problems (wrong model, missing API key, unexpected capture interval) can be diagnosed from the log file without opening the Settings dialog. Secret-like fields are redacted so logs remain safe to share.

## Requirements

### Requirement: Log all active configuration fields at DEBUG on startup
After `ConfigManager.load()` completes, the system SHALL log each configuration key and its value at `DEBUG` level under the `drawing_coach.config_manager` logger. All fields of `LLMConfig` SHALL be logged.

#### Scenario: Config logged after load
- **WHEN** the application starts and `ConfigManager.load()` completes
- **THEN** each `LLMConfig` field name and value is emitted as a DEBUG log entry

#### Scenario: Non-secret field logged as-is
- **WHEN** a config field's name does not contain `key`, `token`, `secret`, or `password` (case-insensitive)
- **THEN** its value is logged without modification

### Requirement: Secret-like fields are redacted in the startup log
Fields whose name contains `key`, `token`, `secret`, or `password` (case-insensitive substring match) SHALL have their value redacted in the log. If the field value has 5 or more characters, only the first 5 characters followed by `…` SHALL be logged. If the field value is empty or fewer than 5 characters, `(not set)` SHALL be logged instead.

#### Scenario: Secret field with a value longer than 5 characters
- **WHEN** a secret-like field (e.g. `api_key`) has a value of 6 or more characters
- **THEN** the log shows the first 5 characters followed by `…` (e.g. `sk-pr…`)

#### Scenario: Secret field that is empty or unset
- **WHEN** a secret-like field has an empty string value or is not configured
- **THEN** the log shows `(not set)` for that field

#### Scenario: Secret field with fewer than 5 characters
- **WHEN** a secret-like field has a non-empty value of fewer than 5 characters
- **THEN** the log shows `(not set)` (treated as effectively unset — not safe to show any chars)
