## Context

`ConfigManager.load()` merges `config.json`, `.env`, and environment variables into an `LLMConfig` dataclass. `MainWindow.__init__` calls `load()` at line 164. Logging is already set up via `setup_logging()` before `MainWindow` is constructed. `LLMConfig` fields are plain Python types (str, int, float, bool); `dataclasses.asdict` gives a flat dict.

## Goals / Non-Goals

**Goals:**
- Log every `LLMConfig` field at DEBUG after load
- Redact secret-like field values
- Empty secret fields logged as `(not set)`

**Non-Goals:**
- Logging config changes after startup (Settings save)
- Configuring which fields are secret via config
- Structured/machine-readable log format

## Decisions

### 1. Implemented as `ConfigManager.log_config(config)` called at the end of `load()`

Placing the call inside `load()` ensures it fires exactly once per load, regardless of call site. The logger is `logging.getLogger("drawing_coach.config_manager")` so it respects the existing log level hierarchy.

**Alternative:** call from `MainWindow.__init__` after `load()` — works but duplicates the responsibility if `load()` is ever called from another site.

### 2. Secret detection: field name contains `key`, `token`, `secret`, or `password` (case-insensitive substring)

Simple string match on the field name. Covers `api_key` and any future fields. No allowlist needed — false positives (e.g. a hypothetical `hotkey`) are benign (first-5 chars of a hotkey string is harmless).

### 3. Redaction format: first 5 chars + `…` (Unicode ellipsis U+2026), or `(not set)` if empty

Five characters is enough to confirm the key is correct (e.g. `sk-pr` vs `sk-an`) without exposing sensitive material. Unicode ellipsis is visually distinct from `...`.

## Risks / Trade-offs

- [Short prefix could leak partial secrets to log files] → 5 chars is the conventional safe minimum for API key confirmation; acceptable
- [Hotkey field name contains "key" → redacted] → `hotkey` value is `<ctrl>+<shift>+f`; showing `<ctrl` is not sensitive and the redaction is harmless
