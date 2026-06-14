## Why

The system keyring requires a running desktop keychain daemon, which fails silently in headless environments (CI, Docker, remote servers) and adds a platform dependency for a task that `.env` files already solve well. Replacing keyring with dotenv simplifies the dependency surface and follows the convention developers already know.

## What Changes

- Remove `keyring` as a dependency entirely
- Add `python-dotenv` as a dependency and load a `.env` file from the XDG config dir at startup
- Implement `DRAWING_COACH_API_KEY` environment variable override (currently documented in the README but not actually read by the code)
- API key resolution becomes: env var / `.env` file only — no keyring fallback
- When the user saves an API key via the settings dialog, write it to the `.env` file
- Centralize all `os.environ` reads into a new `env.py` module
- Ship a `.env.example` template so users know the expected variables
- Update README to reflect the new workflow

## Capabilities

### New Capabilities
- `env-file-secrets`: Load secrets from a `.env` file and environment variables

### Modified Capabilities
- `llm-config`: API key resolution uses env vars / `.env` file only; keyring is removed; settings dialog writes to `.env`

## Impact

- **Dependencies**: removes `keyring>=24.0`; adds `python-dotenv>=1.0`
- **`src/drawing_coach/env.py`**: new module — sole location for all `os.environ` reads
- **`src/drawing_coach/llm_config.py`**: `api_key` getter reads from `env.api_key()`; setter/deleter use dotenv write API; `keyring` import removed
- **`src/drawing_coach/paths.py`**: refactored to use `env.xdg_config_home()` / `env.xdg_data_home()` instead of inline `os.environ` calls
- **`pyproject.toml`**: `keyring` removed, `python-dotenv` added
- **`.env.example`**: new file added to repo root
- **`README.md`**: updated configuration section
- **Security note**: `.env` files are plain text; `.gitignore` already excludes `.env`; users should `chmod 600 ~/.config/drawing-coach/.env`
- **Breaking**: existing keyring-stored API keys will stop working; users must re-enter their key once
