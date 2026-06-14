## Why

The application currently produces no log output, making it impossible for users to diagnose startup issues, verify API connectivity, or understand where their session data is being saved. Users have no visibility into what the app is doing between interactions.

## What Changes

- Add a structured logging layer (Python `logging` module) wired into all major subsystems
- Expose log level and log file destination via `.env` variables (`DRAWING_COACH_LOG_LEVEL`, `DRAWING_COACH_LOG_FILE`)
- Emit user-meaningful log events at key lifecycle points (session start/resume, screenshot saved, API key test, LLM call outcome, window lost, stuck detection triggered)
- Default to `WARNING` level in production so normal runs are quiet; `DEBUG` unlocks full trace for troubleshooting
- Log session directory path at startup so users can find their screenshots

## Capabilities

### New Capabilities

- `app-logging`: Configurable structured logging — level and output file settable via `.env`, covering all major user-facing events across capture, LLM, and session lifecycle

### Modified Capabilities

- `screenshot-capture`: Adds log events for session dir creation/resume and each frame saved or skipped (dedup)
- `llm-config`: Adds log events for config load, API key presence check, and LLM call success/failure/rate-limit

## Impact

- `src/drawing_coach/env.py` — add `log_level()` and `log_file()` readers
- `src/drawing_coach/__init__.py` or new `src/drawing_coach/logging_config.py` — logging bootstrap called at app startup
- `src/drawing_coach/capture_engine.py` — add logger, emit session dir, frame saved, window lost events
- `src/drawing_coach/feedback_engine.py` — emit LLM call start, success, error, rate-limit, policy refusal events
- `src/drawing_coach/llm_config.py` — emit config load and API key presence events
- `src/drawing_coach/main_window.py` or `__main__.py` — call logging bootstrap early in startup
- `.env.example` (new) — document the two new env vars with sensible defaults
