## ADDED Requirements

### Requirement: Black formatting enforced
The project SHALL use `black` as its sole code formatter. All `.py` files under `src/` and `tests/` SHALL be formatted with `black` defaults. The formatter SHALL be configured in `[tool.black]` within `pyproject.toml` with `target-version = ["py311"]`.

#### Scenario: Unformatted file fails check
- **WHEN** `black --check src/ tests/` is run against an unformatted file
- **THEN** the command exits non-zero and reports the offending file

#### Scenario: Formatted file passes check
- **WHEN** all files have been formatted with `black src/ tests/`
- **THEN** `black --check src/ tests/` exits zero

### Requirement: Ruff linting enforced
The project SHALL use `ruff` for linting and import ordering. Ruff SHALL be configured in `[tool.ruff]` within `pyproject.toml` targeting Python 3.11. The enabled rule sets SHALL include at minimum `E`, `F`, `I` (isort). `ruff check src/ tests/` SHALL exit zero on a clean codebase.

#### Scenario: Unsorted imports fail lint
- **WHEN** a module has imports in non-standard order
- **THEN** `ruff check` reports an `I` violation and exits non-zero

#### Scenario: Clean codebase passes lint
- **WHEN** all files comply with configured ruff rules
- **THEN** `ruff check src/ tests/` exits zero

### Requirement: uv manages dependencies
The project SHALL use `uv` for virtual environment creation and dependency management. A `uv.lock` file SHALL be committed to the repository. Dev-only dependencies (formatters, linters, type checkers, test tools) SHALL be declared in a `[dependency-groups]` `dev` group. `uv sync` SHALL install all runtime and dev dependencies from the lock file.

#### Scenario: Reproducible install from lock file
- **WHEN** a developer runs `uv sync --frozen`
- **THEN** the exact versions from `uv.lock` are installed with no network resolution

#### Scenario: Adding a runtime dependency
- **WHEN** a developer runs `uv add <package>`
- **THEN** `pyproject.toml` `[project.dependencies]` is updated and `uv.lock` is regenerated

#### Scenario: Adding a dev dependency
- **WHEN** a developer runs `uv add --group dev <package>`
- **THEN** `[dependency-groups].dev` is updated and `uv.lock` is regenerated

### Requirement: Pytest configured with standard options
The project SHALL configure `pytest` in `[tool.pytest.ini_options]` with at minimum: `testpaths = ["tests"]`, `addopts = "--strict-markers -q"`, and `filterwarnings = ["error"]`. Any custom markers used in tests SHALL be declared in a `markers` list.

#### Scenario: Unknown marker raises error
- **WHEN** a test uses an undeclared `@pytest.mark.<name>`
- **THEN** pytest exits with an error under `--strict-markers`

#### Scenario: Tests run from project root
- **WHEN** `uv run pytest` is executed from the project root
- **THEN** pytest discovers and runs all tests under `tests/`

### Requirement: Type annotations on all public signatures
Every public function and class attribute in `src/drawing_coach/` SHALL carry explicit type annotations on parameters and return values. `from __future__ import annotations` SHALL be present at the top of every module. Annotations SHALL use built-in generics (`list[str]`, `dict[str, int]`) and union syntax (`X | None`) rather than `typing.Optional` or `typing.List`.

#### Scenario: Public function fully annotated
- **WHEN** a public function is defined in any module under `src/drawing_coach/`
- **THEN** all parameters (except `self`/`cls`) and the return type SHALL have annotations

#### Scenario: Class attribute annotated
- **WHEN** a class attribute is declared at class body level
- **THEN** it SHALL have a type annotation (e.g. `_paused: bool = False`)

### Requirement: Pyright type checking configured
The project SHALL include a `[tool.pyright]` section in `pyproject.toml` with `pythonVersion = "3.11"`, `typeCheckingMode = "basic"`, and `reportMissingModuleSource = false`. `pyright` SHALL be included in the dev dependency group.

#### Scenario: pyright runs without configuration error
- **WHEN** `uv run pyright src/` is executed
- **THEN** pyright reads config from `pyproject.toml` and exits without a configuration-error diagnostic
