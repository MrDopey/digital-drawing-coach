## Context

Drawing Coach is a ~15-module Python package under `src/drawing_coach/`. It uses `hatchling` as its build backend and `pip` for dependency management (inferred — no `uv.lock` exists). The project has minimal tooling configured: `testpaths` only in `[tool.pytest.ini_options]`, no formatter, no linter, and no type-checker config. Several modules already use `from __future__ import annotations` and have partial type hints, so the baseline is reasonable — this change closes the remaining gaps and formalises the toolchain.

## Goals / Non-Goals

**Goals:**
- `pyproject.toml` is the single source of truth for all tool config
- `black` enforces consistent formatting across all `.py` files
- `ruff` enforces import ordering and catches common lint issues
- All public function signatures and class attributes carry type annotations
- `uv` manages the virtual environment and lock file; `uv run` is the standard entry point
- `pytest` is configured with `--strict-markers` and coverage addopts
- `pyright` (basic mode) is configured for type-checking in CI

**Non-Goals:**
- Converting private/internal methods to fully typed where annotations would add no value
- Achieving zero pyright errors on day one — strict mode is out of scope
- Changing any runtime behaviour or refactoring module structure
- Adding pre-commit hooks (separate change if desired)

## Decisions

### 1. `black` + `ruff` over a single tool (e.g. `ruff format`)

`ruff format` is a black-compatible formatter, but `black` remains the canonical reference implementation with the most predictable output. Using both is explicit: `black` owns formatting, `ruff` owns linting + import sorting (replacing `isort`). This mirrors the preference spec exactly.

**Alternative considered**: Ruff-only. Rejected because the preference spec names `black` explicitly, and mixing format-only with lint-only responsibilities is cleaner for config reasoning.

### 2. `uv` replaces bare `pip`, lock file committed

`uv.lock` is committed to pin the full dependency graph. `uv sync --frozen` in CI ensures reproducible installs. Dev dependencies move to `[dependency-groups]` (PEP 735) rather than `[project.optional-dependencies]` to align with `uv` idioms.

**Alternative considered**: Keep `pip` + `requirements.txt`. Rejected — no lock file means non-reproducible environments, which is the precise problem `uv` solves.

### 3. `pyright` in basic mode, not strict

The codebase has partial annotations. Strict mode would require fixing all existing untyped code before CI passes. Basic mode catches real errors without blocking the change on pre-existing untyped third-party stubs (PyQt6 stubs are incomplete).

**Alternative considered**: `mypy`. Rejected — `pyright` has better PyQt6 and `numpy` support out of the box, and `uv` integrates cleanly with it.

### 4. Type annotations added in-place, no behaviour changes

All annotation work uses `from __future__ import annotations` (already present in several modules) to defer evaluation. Return types, parameter types, and class attributes are annotated without changing any logic.

## Risks / Trade-offs

- **PyQt6 stubs are incomplete** → `pyright` will emit false positives on some Qt signal/slot patterns. Mitigation: `# type: ignore[misc]` on known-bad patterns; document in `[tool.pyright]` with `reportMissingModuleSource = false`.
- **`uv.lock` churn in PRs** → Any dependency bump regenerates the lock file. Acceptable — this is expected `uv` behaviour and easily reviewed.
- **`black` reformats existing code** → Diff noise on first run. Mitigation: land the formatting commit atomically before annotation changes so blame is clean.

## Migration Plan

1. Add `uv` toolchain config to `pyproject.toml`; run `uv lock` to generate `uv.lock`
2. Add `black`, `ruff`, `pyright` to dev dependency group; run `uv sync`
3. Run `black src/ tests/` — commit formatting changes alone
4. Add `[tool.black]`, `[tool.ruff]`, `[tool.pyright]` config sections to `pyproject.toml`
5. Expand `[tool.pytest.ini_options]`
6. Add type annotations module by module (no logic changes)
7. Run `pyright` and address any errors introduced by new annotations

**Rollback**: Remove `uv.lock` and revert `pyproject.toml` — no runtime code changes, so rollback is low-risk.

## Open Questions

- Should `ruff` rules include `D` (pydocstyle) to enforce Google-style docstrings automatically, or leave docstring style to convention? *(Recommend: exclude `D` for now; add in a separate change once existing docstrings are audited.)*
