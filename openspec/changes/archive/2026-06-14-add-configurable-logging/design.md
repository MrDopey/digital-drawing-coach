## Context

Drawing Coach is a Python/PyQt6 desktop app with no current logging. Users cannot tell where their screenshots are saved, whether their API key worked, or why feedback failed. The app uses `python-dotenv` to read secrets from `.env` in the XDG config dir — the same mechanism can carry logging configuration with zero new dependencies.

## Goals / Non-Goals

**Goals:**
- Add a single logging bootstrap called once at startup that configures the Python `logging` hierarchy for the whole app
- Let users set log level and optional log file via two env vars in `.env`
- Emit structured, human-readable log lines at every user-observable event: session dir, screenshot saved/skipped, LLM call start/outcome, API key presence, window lost, stuck detection
- Default to `WARNING` — silent under normal operation, noisy only when something is wrong

**Non-Goals:**
- JSON/structured log output (plain text is sufficient for a desktop app)
- Log rotation (users who set a log file path manage it themselves)
- Per-module log level overrides (single app-wide level is enough)
- Sending logs to a remote service

## Decisions

### 1. Use Python stdlib `logging`, no new dependency

**Decision:** Wire `logging.basicConfig` / `logging.getLogger("drawing_coach")` hierarchy. All module loggers are named `drawing_coach.<module>` so the root `drawing_coach` logger controls them all.

**Alternatives considered:**
- `structlog` — adds a dependency and JSON output is overkill for a desktop app
- `loguru` — same concern; stdlib is already installed and sufficient

### 2. Bootstrap in `src/drawing_coach/logging_config.py`, call from `__main__.py`

**Decision:** A dedicated `logging_config.py` module with a single `setup_logging()` function. `__main__.py` calls it as the very first line before any other import side-effects.

**Why:** Keeps bootstrap isolated and testable. Avoids import-order surprises if logging were bootstrapped inside `__init__.py`.

### 3. Env vars: `DRAWING_COACH_LOG_LEVEL` and `DRAWING_COACH_LOG_FILE`

**Decision:**
- `DRAWING_COACH_LOG_LEVEL` — one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Default: `WARNING`.
- `DRAWING_COACH_LOG_FILE` — absolute or relative path. If set, a `RotatingFileHandler` is added alongside the default `StreamHandler`. If empty/unset, only stdout/stderr output.
- `DRAWING_COACH_LOG_MAX_BYTES` — maximum log file size in bytes before rotation. Default: `10485760` (10 MB). When the file reaches this size the handler rotates with `backupCount=0`, meaning the old content is discarded and a new file starts — keeping only the latest ≤10 MB of log data.

**Why `WARNING` default:** Normal runs produce zero log noise. Users who want trace enable `DEBUG`.

**Why in `.env`:** Consistent with how `DRAWING_COACH_API_KEY` and `DRAWING_COACH_MODEL` are already configured. Users only need to know one config file.

### 4. Log format

```
2026-06-14 10:23:01 INFO drawing_coach.capture_engine — Session started at /home/user/.local/share/drawing-coach/sessions/2026-06-14_102301
```

Pattern: `%(asctime)s %(levelname)s %(name)s — %(message)s` with `datefmt="%Y-%m-%d %H:%M:%S"` to suppress sub-second precision.

Short enough to scan, includes module name for triage.

### 5. Log event catalogue

| Event | Level | Module | Message |
|-------|-------|--------|---------|
| App startup | INFO | `__main__` | `Drawing Coach vX.Y starting` |
| Logging configured | DEBUG | `logging_config` | `Log level=INFO file=<path or none>` |
| Config loaded | INFO | `llm_config` | `Config loaded from <path>` |
| API key present | INFO | `llm_config` | `API key present (source: env)` |
| API key absent | WARNING | `llm_config` | `No API key configured` |
| Session created | INFO | `capture_engine` | `New session: <path>` |
| Session resumed | INFO | `capture_engine` | `Resumed session: <path> (<N> existing frames)` |
| Old sessions pruned | INFO | `capture_engine` | `Pruned <N> old sessions (retention: <K>)` |
| Frame saved | DEBUG | `capture_engine` | `Frame saved: <filename> (<WxH>)` |
| Frame skipped (dedup) | DEBUG | `capture_engine` | `Frame skipped: MAE=<val> < threshold=<val>` |
| Window lost | WARNING | `capture_engine` | `Drawing window lost — capture paused` |
| LLM call started | INFO | `feedback_engine` | `LLM request: model=<model> mode=<mode> frames=<N>` |
| LLM call succeeded | INFO | `feedback_engine` | `LLM response received in <ms>ms` |
| LLM rate-limited | WARNING | `feedback_engine` | `Rate limit: waiting <N>s before next request` |
| LLM policy refusal | WARNING | `feedback_engine` | `LLM refused request (policy): <excerpt>` |
| LLM error | ERROR | `feedback_engine` | `LLM call failed: <error>` |
| Stuck detected | INFO | `stuck_detector` | `Stuck detected (consecutive: <N>)` |
| Capture paused | INFO | `capture_engine` | `Capture paused by user` |
| Capture resumed | INFO | `capture_engine` | `Capture resumed` |

## Risks / Trade-offs

- **`backupCount=0` discards history on rollover** → once the file reaches the cap, the previous content is gone. Users who need audit history can set `DRAWING_COACH_LOG_MAX_BYTES` to a larger value or pipe to a separate log collector. Mitigation: document in `.env.example`.
- **`WARNING` default hides INFO events** → users who never set `LOG_LEVEL=INFO` will miss session dir and API key messages. Mitigation: the settings dialog / first-run wizard can surface the session path directly; logs are a power-user feature.
- **Thread safety** → `CaptureEngine` runs a background thread. Python's `logging` module is thread-safe by default (internal lock on handlers), so no additional synchronisation is needed.

## Migration Plan

No data migration needed. Logging is purely additive — no existing behaviour changes. `.env.example` documents the new vars. Existing `.env` files without the new vars continue to work (defaults apply).
