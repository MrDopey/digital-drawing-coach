## Context

The headless mode added a FastAPI HTTP server as an alternative runtime path, intended for CI pipelines and programmatic use. In practice, the core use case (a person drawing in real time) always involves a display, making the server mode redundant. It also pulls in FastAPI, uvicorn, Pydantic, and httpx — significant weight for unused functionality.

## Goals / Non-Goals

**Goals:**
- Delete all server-related code, tests, and configuration
- Simplify the entry point to GUI-only
- Strip server-only dependencies from `pyproject.toml`
- Remove headless docs from README and CLAUDE.md
- Archive the `headless-api` spec via delta spec

**Non-Goals:**
- Changing any GUI behaviour
- Removing environment variable support for `DRAWING_COACH_MODEL`, `DRAWING_COACH_API_KEY`, or `DRAWING_COACH_API_BASE` — these are still used by the GUI path via `llm_config.py`

## Decisions

**Delete Dockerfile and .dockerignore outright** — Docker only made sense for headless mode. No alternative container strategy is needed.

**Keep `DRAWING_COACH_MODEL` / `DRAWING_COACH_API_KEY` / `DRAWING_COACH_API_BASE` env vars** — `llm_config.py` already applies these at startup for the GUI path; they remain useful for scripted or dev use. Only `DRAWING_COACH_HEADLESS` and `DRAWING_COACH_PORT` are removed.

**Remove `httpx` from `[dev]`** — it was only required by `test_server.py`. The remaining test suite does not use it.

## Risks / Trade-offs

No functional risk — the removed code is not reachable from the GUI path. The only risk is accidentally leaving a stale import; addressed by deleting the whole `server.py` module and its test file rather than commenting code out.
