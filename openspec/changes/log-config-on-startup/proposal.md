## Why

When debugging configuration problems (wrong model, missing API key, unexpected capture interval) there is currently no way to confirm what settings are actually in effect at runtime without opening the Settings dialog. A startup log of all active config values would make these issues immediately diagnosable from the log file.

## What Changes

- After `ConfigManager.load()` completes, all `LLMConfig` fields are logged at `DEBUG` level
- Fields whose name contains `key`, `token`, `secret`, or `password` (case-insensitive) are redacted: only the first 5 characters are shown followed by `…` (e.g. `sk-pr…`)
- If a secret field is empty or unset, `(not set)` is logged instead of an empty string

## Capabilities

### New Capabilities
- `config-startup-log`: Log all active configuration fields at DEBUG level on startup, with redaction for secret-like fields

### Modified Capabilities

## Impact

- `src/drawing_coach/config_manager.py` — add `log_config(config: LLMConfig)` method (or module-level function) called after `load()`
- No new dependencies; uses stdlib `logging` and `dataclasses.asdict`
