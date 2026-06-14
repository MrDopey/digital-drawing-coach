## Context

The app currently stores the API key exclusively in the OS system keyring (`keyring.set_password("drawing-coach", "api_key", ...)`). This fails silently in headless environments (CI runners, Docker containers, WSL without a keyring daemon) and adds a platform dependency for a task that `.env` files already solve well. Additionally, `DRAWING_COACH_API_KEY` is documented in the README as a supported override but is never actually read from the environment.

## Goals / Non-Goals

**Goals:**
- Remove `keyring` as a dependency entirely
- Load a `.env` file from the XDG config dir (`~/.config/drawing-coach/.env`) at startup
- Make `DRAWING_COACH_API_KEY` environment variable actually work
- Centralize all `os.environ` reads into a single `env.py` module
- Settings dialog writes the API key to the `.env` file
- Ship a `.env.example` in the repo root to document available variables

**Non-Goals:**
- Backward compatibility with existing keyring entries (users re-enter once)
- Supporting `.env` files in arbitrary locations (cwd, project root, etc.)
- Encrypting the `.env` file (plain text; users must manage file permissions)
- Multi-account or multi-profile support

## Decisions

### 1. `.env` file location: XDG config dir

**Decision**: Store `.env` at `config_path().parent / ".env"` (i.e., `~/.config/drawing-coach/.env` on Linux).

**Alternatives considered**:
- *cwd / project root*: Unpredictable for a packaged desktop app; risks accidental git commit.
- *`~/.env`*: Too global; would interfere with other apps.
- *Next to `config.json`*: Same directory, consistent, XDG-compliant. ✓

### 2. Centralize all `os.environ` reads in `env.py`

**Decision**: Introduce `src/drawing_coach/env.py` as the single module that calls `os.environ.get()`. All other modules (`paths.py`, `llm_config.py`) import typed accessor functions from `env.py` instead of reading `os.environ` directly.

```
env.py          ← sole os.environ reader; exposes typed accessors
  ↑ imported by
paths.py        ← uses env.xdg_config_home(), env.xdg_data_home()
llm_config.py   ← uses env.api_key(), env.model(), env.api_base()
```

`env.py` has no imports from other app modules so there are no circular dependencies.

**Alternatives considered**:
- *Keep `os.environ` calls inline*: Works but scatters the env contract across files; harder to stub in tests.
- *Put everything in `paths.py`*: Already handles XDG, but mixing XDG path vars with app config vars is poor separation of concerns.

### 3. Load timing: module-level `load_dotenv()` in `llm_config.py`

**Decision**: Call `load_dotenv(dotenv_path=config_path().parent / ".env", override=False)` at the top of `llm_config.py` (module import), before the `LLMConfig` class is instantiated. `llm_config.py` is the natural owner since it controls both `.env` reads (via `env.py`) and writes (`set_key`/`unset_key`).

`override=False` means real environment variables (set by CI, Docker `--env`, shell) always win over `.env` file values.

**Alternatives considered**:
- *Call in `env.py`*: Would require `env.py` to import `paths.py` for the dotenv path, creating a circular dependency (`paths.py` → `env.py` → `paths.py`).
- *Call in `main.py`*: Requires GUI entrypoint; breaks CLI and test usage.

### 4. API key resolution: environment only

**Decision**: The `api_key` getter reads exclusively from `env.api_key()` (i.e., `os.environ.get("DRAWING_COACH_API_KEY", "")`). No keyring lookup.

```
DRAWING_COACH_API_KEY env var  ← set by .env load or real env
        ↓ (empty or missing)
       "" (empty string)
```

**Rationale**: Removing the fallback eliminates the `keyring` dependency entirely and makes the resolution path trivially testable with `patch.dict("os.environ", ...)`.

### 5. Write target: `.env` file only

**Decision**: The `api_key` setter calls `dotenv.set_key()`; the deleter calls `dotenv.unset_key()`. The `keyring` import is removed completely.

### 6. python-dotenv `set_key()` for atomic writes

`dotenv.set_key(dotenv_path, "DRAWING_COACH_API_KEY", value)` handles creating the file, updating existing entries, and preserving other variables — no manual file parsing required.

## Risks / Trade-offs

- **Plain-text secrets** → The `.env` file is unencrypted. Mitigation: documentation warns users to set `chmod 600 ~/.config/drawing-coach/.env`; the `.gitignore` already excludes `.env`.
- **Breaking change for keyring users** → Existing API keys silently stop working on upgrade. Mitigation: release notes call it out; error message when no key is configured directs users to re-enter in settings.
- **`override=False` means shell env wins** → Intentional, but could surprise users who set a key in `.env` and forget they have a conflicting shell export. Mitigation: document priority order in README.
- **`set_key()` requires file to be writable** → If the config dir is on a read-only filesystem, the setter fails. Mitigation: catch `PermissionError` and surface a clear error message.

## Migration Plan

1. Remove `keyring>=24.0` from `pyproject.toml`; add `python-dotenv>=1.0`.
2. Create `src/drawing_coach/env.py` with typed accessors for all `os.environ` reads.
3. Refactor `paths.py` to use `env.xdg_config_home()` / `env.xdg_data_home()`.
4. Update `llm_config.py`: add `load_dotenv()` call; replace inline `os.environ` reads with `env.*()` calls; rewrite `api_key` getter/setter/deleter without keyring.
5. Add `.env.example` to repo root.
6. Update README configuration section.
7. Update tests: use `patch.dict("os.environ", ...)` and mock `dotenv.set_key` / `dotenv.unset_key`.

**Rollback**: Revert `llm_config.py` and `pyproject.toml`. The user's keyring entry is untouched. Any `.env` file created by the user remains on disk but is no longer read.
