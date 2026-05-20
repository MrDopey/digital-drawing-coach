## Why

The digital drawing coach is a Python desktop app that artists can't easily install without knowing how to set up a Python environment. Providing pre-built native binaries and a Docker image removes that barrier — artists download and run, developers integrate or test headlessly via API.

## What Changes

- **New**: GitHub Actions CI pipeline that builds platform-native binaries (Windows `.exe`, macOS `.app`, Linux binary) using PyInstaller on each release tag
- **New**: Binaries published as assets on GitHub Releases and registered as GitHub Packages (using OCI-compatible packaging via `gh`)
- **New**: Headless server mode — a lightweight HTTP API (`/capture`, `/feedback`, `/config`) that runs the capture and LLM pipeline without a GUI
- **New**: Docker image built from the headless mode, published to GitHub Container Registry (`ghcr.io`) on each release tag and on merges to `main`
- **New**: Version stamping — build embeds the git tag as the app version shown in the About dialog and API `/health` endpoint

## Capabilities

### New Capabilities

- `binary-release`: PyInstaller builds for Windows, macOS, and Linux triggered by release tags; artifacts uploaded to GitHub Releases and registered as GitHub Packages
- `headless-api`: HTTP API server mode (FastAPI) that exposes capture, feedback, and config endpoints without a GUI — used by the Docker image and for programmatic/CI access
- `docker-distribution`: Multi-stage Docker image built from headless mode, published to `ghcr.io` on tag and `main` push; supports environment-variable LLM config for container deployments

### Modified Capabilities

## Impact

- New: `.github/workflows/release.yml` — matrix build (3 OS runners) + Docker build/push
- New: `src/server.py` — FastAPI app wrapping the existing `capture_engine`, `feedback_engine`, and `llm_config` modules
- New: `Dockerfile` and `.dockerignore`
- New: `pyproject.toml` optional dependency group `[server]` for FastAPI + uvicorn
- Existing modules unchanged — headless mode reuses `capture_engine.py`, `feedback_engine.py`, `llm_config.py` directly
- No changes to GUI code paths
