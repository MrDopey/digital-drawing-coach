## 1. Path Resolver Module

- [x] 1.1 Create `src/drawing_coach/paths.py` with `config_path()` and `sessions_dir()` functions that apply XDG logic on Linux/macOS and fall back to `~/.drawing-coach/` on Windows

## 2. Wire Up Path Module

- [x] 2.1 Update `src/drawing_coach/llm_config.py` to import `config_path` and `sessions_dir` from `paths.py` and remove the hardcoded `_CONFIG_PATH` and `_SESSIONS_DIR` constants
- [x] 2.2 Update `src/drawing_coach/capture_engine.py` to import `sessions_dir` from `paths.py` instead of deriving its own path

## 3. Update Tests

- [x] 3.1 Update `tests/test_llm_config.py` to patch `drawing_coach.paths.config_path` (and `sessions_dir`) instead of the old `_CONFIG_PATH` constant
- [x] 3.2 Add unit tests for `paths.py` covering: XDG_CONFIG_HOME set, XDG_CONFIG_HOME unset, XDG_DATA_HOME set, XDG_DATA_HOME unset, Windows platform (mock `sys.platform`)

## 4. Documentation

- [x] 4.1 Update `README.md` to document the XDG directory layout and note the one-time migration from `~/.drawing-coach/`
- [x] 4.2 Update `.claude/CLAUDE.md` if any project-level setup notes reference the config path

## 5. Verification

- [x] 5.1 Run `uv run pytest` and confirm all tests pass
