## Why

The headless HTTP server mode is not useful for a drawing coach — the core use case requires a human at a screen drawing in real-time, so a GUI is always present. The feature adds dependency weight (FastAPI, uvicorn, Pydantic), a Dockerfile, and maintenance surface with no real-world benefit.

## What Changes

- **BREAKING** Remove the `--headless` flag and `DRAWING_COACH_HEADLESS` env var from the entry point
- **BREAKING** Remove the `DRAWING_COACH_PORT` env var
- Delete `src/drawing_coach/server.py`
- Delete `tests/test_server.py`
- Delete `Dockerfile` and `.dockerignore`
- Remove the `[server]` optional dependency group (`fastapi`, `uvicorn`) from `pyproject.toml`
- Remove `[dev]` dependency on `httpx` (only needed for server tests)
- Update `README.md`: remove the **Headless server**, **Docker**, **API Reference** sections; remove `DRAWING_COACH_HEADLESS` and `DRAWING_COACH_PORT` from the environment variables table; remove the `[server]` install variant from the Installation section
- Update `.claude/CLAUDE.md`: remove the headless API endpoints table and the two headless-only env var rows

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `headless-api`: Capability is being removed entirely — spec will be deleted

## Impact

- `src/drawing_coach/__main__.py`: Remove headless branch, simplify to GUI-only entry point
- `pyproject.toml`: Remove `server` extra, remove `httpx` from `dev` extra
- `Dockerfile`, `.dockerignore`: Deleted
- `README.md`: Remove headless mode, Docker, API reference, and headless env vars sections
- `.claude/CLAUDE.md`: Remove headless API endpoints section and headless env vars
