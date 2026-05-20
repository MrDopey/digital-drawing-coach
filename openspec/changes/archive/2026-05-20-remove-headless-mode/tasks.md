## 1. Delete server files

- [x] 1.1 Delete `src/drawing_coach/server.py`
- [x] 1.2 Delete `tests/test_server.py`
- [x] 1.3 Delete `Dockerfile`
- [x] 1.4 Delete `.dockerignore`

## 2. Simplify entry point

- [x] 2.1 Remove the headless branch from `src/drawing_coach/__main__.py` — strip the `--headless` flag check, `DRAWING_COACH_HEADLESS` env var check, `DRAWING_COACH_PORT` env var, and the `uvicorn.run(...)` call; keep only the GUI path

## 3. Update dependencies

- [x] 3.1 Remove the `[server]` optional dependency group (`fastapi`, `uvicorn[standard]`) from `pyproject.toml`
- [x] 3.2 Remove `httpx` from the `[dev]` optional dependency group in `pyproject.toml`

## 4. Update documentation

- [x] 4.1 Remove the **Headless server**, **Docker**, **API Reference**, and headless-related **Environment Variables** (`DRAWING_COACH_PORT`, `DRAWING_COACH_HEADLESS`) from `README.md`
- [x] 4.2 Remove the **Headless API Endpoints** section and `DRAWING_COACH_PORT`/`DRAWING_COACH_HEADLESS` rows from `.claude/CLAUDE.md`
