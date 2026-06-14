## 1. Dependencies

- [x] 1.1 Remove `keyring>=24.0` from the core dependencies in `pyproject.toml`
- [x] 1.2 Add `python-dotenv>=1.0` to the core dependencies in `pyproject.toml`
- [x] 1.3 Run `uv sync` to update the lockfile

## 2. Centralized env module

- [x] 2.1 Create `src/drawing_coach/env.py` with typed accessor functions for every `os.environ` read in the codebase: `xdg_config_home() -> str`, `xdg_data_home() -> str`, `api_key() -> str`, `model() -> str`, `api_base() -> str` — each wrapping `os.environ.get("<VAR>", "")`
- [x] 2.2 Refactor `paths.py`: replace `os.environ.get("XDG_CONFIG_HOME", ...)` and `os.environ.get("XDG_DATA_HOME", ...)` with `env.xdg_config_home()` and `env.xdg_data_home()`; remove the direct `os` import if no longer needed

## 3. Core Implementation

- [x] 3.1 In `llm_config.py`, add `load_dotenv(dotenv_path=config_path().parent / ".env", override=False)` at module level (after imports, before class definition)
- [x] 3.2 Replace the inline `os.environ.get("DRAWING_COACH_MODEL")` calls in `LLMConfig.load()` with `env.model()`
- [x] 3.3 Replace the inline `os.environ.get("DRAWING_COACH_API_BASE")` calls with `env.api_base()`
- [x] 3.4 Rewrite the `api_key` getter to return `env.api_key()` directly — no keyring lookup
- [x] 3.5 Rewrite the `api_key` setter to call `dotenv.set_key(config_path().parent / ".env", "DRAWING_COACH_API_KEY", value)` — remove `keyring.set_password()`
- [x] 3.6 Rewrite the `api_key` deleter to call `dotenv.unset_key(config_path().parent / ".env", "DRAWING_COACH_API_KEY")` — remove `keyring.delete_password()`
- [x] 3.7 Wrap the setter/deleter in a `PermissionError` handler that surfaces a clear error message if the `.env` file is not writable
- [x] 3.8 Remove the `keyring` import from `llm_config.py` entirely

## 4. New Files

- [x] 4.1 Create `.env.example` in the repo root documenting `DRAWING_COACH_API_KEY`, `DRAWING_COACH_MODEL`, and `DRAWING_COACH_API_BASE` with comments and example values

## 5. Tests

- [x] 5.1 Create `tests/test_env.py`: verify each accessor (`api_key`, `model`, `api_base`, `xdg_config_home`, `xdg_data_home`) returns the env var value when set and an empty string when absent, using `patch.dict("os.environ", ...)`
- [x] 5.2 Update `tests/test_paths.py`: replace `patch.dict("os.environ", ...)` with patches on `drawing_coach.env.xdg_config_home` / `drawing_coach.env.xdg_data_home`
- [x] 5.3 Update `tests/test_llm_config.py`: remove all `keyring` mocks; mock `dotenv.set_key` and `dotenv.unset_key` for setter/deleter tests
- [x] 5.4 Add test: `DRAWING_COACH_API_KEY` env var is returned by the getter when set
- [x] 5.5 Add test: getter returns empty string when `DRAWING_COACH_API_KEY` is unset
- [x] 5.6 Add test: setter writes to the dotenv file
- [x] 5.7 Add test: deleter removes key from the dotenv file
- [x] 5.8 Add test: `PermissionError` during setter produces a descriptive error

## 6. Documentation

- [x] 6.1 Update `README.md`: revise the configuration section to describe the `.env` file workflow; document priority order (env var > `.env` file); note that existing keyring entries no longer work and must be re-entered; link to `.env.example`
- [x] 6.2 Update `.claude/CLAUDE.md`: change the Secrets row in the tech stack table from `keyring` to `python-dotenv`

## 7. Verification

- [x] 7.1 Run `uv run pytest` and confirm all tests pass
