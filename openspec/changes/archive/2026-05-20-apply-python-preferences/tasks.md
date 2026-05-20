## 1. Toolchain Setup

- [x] 1.1 Add `[tool.uv]` section and `[dependency-groups]` dev group to `pyproject.toml`; move existing dev deps (`pytest`, `pytest-qt`) into `dev` group
- [x] 1.2 Run `uv lock` to generate `uv.lock` and verify `uv sync` installs cleanly
- [x] 1.3 Add `black`, `ruff`, and `pyright` to the dev dependency group via `uv add --group dev`

## 2. Formatter and Linter Configuration

- [x] 2.1 Add `[tool.black]` section to `pyproject.toml` with `target-version = ["py311"]` and `line-length = 88`
- [x] 2.2 Add `[tool.ruff]` section with `target-version = "py311"`, `line-length = 88`, and `select = ["E", "F", "I"]`
- [x] 2.3 Run `black src/ tests/` to apply initial formatting; commit as a standalone formatting-only commit
- [x] 2.4 Run `ruff check --fix src/ tests/` to fix import ordering; verify `ruff check src/ tests/` exits zero

## 3. Pytest Configuration

- [x] 3.1 Expand `[tool.pytest.ini_options]` in `pyproject.toml`: add `addopts = "--strict-markers -q"` and `filterwarnings = ["error"]`
- [x] 3.2 Run `uv run pytest` and confirm all existing tests pass under the new config

## 4. Pyright Configuration

- [x] 4.1 Add `[tool.pyright]` section to `pyproject.toml` with `pythonVersion = "3.11"`, `typeCheckingMode = "basic"`, `reportMissingModuleSource = false`
- [x] 4.2 Run `uv run pyright src/` baseline to record initial error count before annotation work

## 5. Type Annotations — Core Modules

- [x] 5.1 Add full type annotations to `capture_engine.py` (public methods and class attributes)
- [x] 5.2 Add full type annotations to `feedback_engine.py`
- [x] 5.3 Add full type annotations to `llm_config.py`
- [x] 5.4 Add full type annotations to `stuck_detector.py`
- [x] 5.5 Add full type annotations to `window_manager.py`
- [x] 5.6 Add full type annotations to `overlay_renderer.py`

## 6. Type Annotations — GUI Modules

- [x] 6.1 Add full type annotations to `main_window.py`
- [x] 6.2 Add full type annotations to `feedback_panel.py`
- [x] 6.3 Add full type annotations to `history_panel.py`
- [x] 6.4 Add full type annotations to `settings_dialog.py`
- [x] 6.5 Add full type annotations to `hotkey_manager.py`
- [x] 6.6 Add full type annotations to `app_selection_dialog.py`

## 7. Type Annotations — Platform Backends and Init

- [x] 7.1 Add full type annotations to `_backend_linux.py`, `_backend_macos.py`, `_backend_windows.py`
- [x] 7.2 Add full type annotations to `__init__.py` and `__main__.py`

## 8. Verification

- [x] 8.1 Run `uv run pyright src/` and resolve any errors introduced by new annotations
- [x] 8.2 Run `black --check src/ tests/` and `ruff check src/ tests/` — both must exit zero
- [x] 8.3 Run `uv run pytest` — all tests must pass

