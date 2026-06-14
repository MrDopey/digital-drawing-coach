## 1. Env var support

- [x] 1.1 Add `log_level()`, `log_file()`, and `log_max_bytes()` reader functions to `src/drawing_coach/env.py`

## 2. Logging bootstrap

- [x] 2.1 Create `src/drawing_coach/logging_config.py` with a `setup_logging()` function that reads `DRAWING_COACH_LOG_LEVEL`, `DRAWING_COACH_LOG_FILE`, and `DRAWING_COACH_LOG_MAX_BYTES`, configures the `drawing_coach` root logger with the defined format and `datefmt="%Y-%m-%d %H:%M:%S"`, adds a `StreamHandler`, and optionally adds a `RotatingFileHandler(maxBytes=<configured>, backupCount=0)` (with parent dir existence check and graceful fallback on failure)
- [x] 2.2 Call `setup_logging()` as the first statement in `src/drawing_coach/__main__.py` before any other imports or logic

## 3. Startup log

- [x] 3.1 Log `Drawing Coach v<version> starting` at INFO in `__main__.py` immediately after `setup_logging()`
- [x] 3.2 Log `Log level=<level> file=<path or none>` at DEBUG inside `setup_logging()` after configuration is complete

## 4. Config and API key logging

- [x] 4.1 In `LLMConfig.load()`, emit INFO `Config loaded from <path>` when a config file exists, or INFO `No config file found, using defaults` otherwise
- [x] 4.2 In `LLMConfig.load()`, after resolving the API key, emit INFO `API key present` if a key is found, or WARNING `No API key configured — LLM calls will fail unless using a local model` if absent

## 5. Capture engine logging

- [x] 5.1 Add a `logging.getLogger("drawing_coach.capture_engine")` instance at module level in `capture_engine.py`
- [x] 5.2 In `_init_session()`, emit INFO `New session: <absolute_path>` when a new session dir is created
- [x] 5.3 In `_init_session()`, emit INFO `Resumed session: <absolute_path> (<N> existing frames)` when an existing session is resumed
- [x] 5.4 In `_cleanup_old_sessions()`, emit INFO `Pruned <N> old sessions (retention: <K>)` when at least one session is deleted
- [x] 5.5 In `_write_frame()`, emit DEBUG `Frame saved: <filename> (<W>x<H>)` after the PNG is written
- [x] 5.6 In `_do_capture()`, emit DEBUG `Frame skipped: MAE=<val:.2f> < threshold=<val:.2f>` when dedup drops a frame
- [x] 5.7 In `_do_capture()`, emit WARNING `Drawing window lost — capture paused` when `get_window_rect` returns None
- [x] 5.8 In `pause()`, emit INFO `Capture paused by user`; in `resume()`, emit INFO `Capture resumed`

## 6. Feedback engine logging

- [x] 6.1 Add a `logging.getLogger("drawing_coach.feedback_engine")` instance at module level in `feedback_engine.py`
- [x] 6.2 At the start of each LLM call in `request_feedback()`, emit INFO `LLM request: model=<model> mode=<mode> frames=<N>`
- [x] 6.3 On successful LLM response, emit INFO `LLM response received in <elapsed_ms>ms`
- [x] 6.4 On exception from the LLM call, emit ERROR `LLM call failed: <error_message>`
- [x] 6.5 When the rate-limit check suppresses a call, emit WARNING `Rate limit: <N>s remaining before next request`
- [x] 6.6 When a policy refusal phrase is detected in the response, emit WARNING `LLM policy refusal detected`

## 7. .env documentation

- [x] 7.1 Create `.env.example` at the repo root documenting all supported env vars including `DRAWING_COACH_LOG_LEVEL`, `DRAWING_COACH_LOG_FILE`, and `DRAWING_COACH_LOG_MAX_BYTES` with comments explaining valid values and defaults (e.g. `# DRAWING_COACH_LOG_MAX_BYTES=10485760  # 10 MB cap; old content discarded on rotation`)

## 8. Tests

- [x] 8.1 Add tests for `setup_logging()` covering: valid level, invalid level (defaults to WARNING), log file set but parent missing (graceful fallback), log file set and writable (RotatingFileHandler added with correct maxBytes), custom `DRAWING_COACH_LOG_MAX_BYTES` value is respected
- [x] 8.2 Add tests for `LLMConfig.load()` log emissions: config found emits INFO, config absent emits INFO, API key present emits INFO, API key absent emits WARNING

## 9. Documentation

- [x] 9.1 Update `README.md` to document the three new `.env` variables (`DRAWING_COACH_LOG_LEVEL`, `DRAWING_COACH_LOG_FILE`, `DRAWING_COACH_LOG_MAX_BYTES`) with an example snippet
- [x] 9.2 Update `.claude/CLAUDE.md` Tech Stack table if `.env.example` is a notable addition

## 10. Verification

- [x] 10.1 Run `uv run pytest` and confirm all tests pass
