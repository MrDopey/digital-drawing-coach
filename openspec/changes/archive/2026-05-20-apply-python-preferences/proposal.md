## Why

The project has no enforced formatting, inconsistent or absent type hints, no `uv` lock file, and minimal pytest configuration — making the codebase harder to maintain and onboard contributors to. Standardising now, before the module count grows further, is lower-cost than retrofitting later.

## What Changes

- Add `black` as the project formatter and configure it in `pyproject.toml`
- Add full type annotations to all public function signatures and class attributes across `src/drawing_coach/`
- Migrate from raw `hatchling` + manual `pip` to `uv` for dependency management (add `uv.lock`, `[tool.uv]` section)
- Expand `[tool.pytest.ini_options]` with standard options (addopts, markers, filterwarnings)
- Add `ruff` for linting (import order enforcement, common lint rules) as a complement to `black`
- Add dev dependency group covering `black`, `ruff`, `pytest`, `pytest-qt`, and `pyright` for type checking

## Capabilities

### New Capabilities

- `python-tooling`: Project-level tooling configuration — formatter, linter, type checker, and package manager wired into `pyproject.toml`

### Modified Capabilities

*(none — no spec-level behaviour changes)*

## Impact

- `pyproject.toml`: new `[tool.black]`, `[tool.ruff]`, `[tool.pyright]`, extended `[tool.pytest.ini_options]`, `[tool.uv]` sections; dev dependency group added
- `src/drawing_coach/*.py`: type annotations added to all public signatures; no logic changes
- New: `uv.lock` generated from current dependencies
- CI / developer workflow: `uv run` replaces bare `python`; `black` and `ruff` become pre-commit checks
