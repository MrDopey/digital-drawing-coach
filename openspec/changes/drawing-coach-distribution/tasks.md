## 1. Version Embedding

- [ ] 1.1 Create `src/_version.py` with a `__version__` variable defaulting to `"dev"`
- [ ] 1.2 Write `scripts/build_version.py` that reads `GITHUB_REF_NAME` env var (strips leading `v`) and overwrites `src/_version.py`
- [ ] 1.3 Expose version in GUI About dialog by importing `_version.__version__`
- [ ] 1.4 Add unit test: `_version.__version__` is a non-empty string

## 2. Headless API Server

- [ ] 2.1 Add `fastapi` and `uvicorn[standard]` to `pyproject.toml` under optional `[server]` extras group
- [ ] 2.2 Create `src/server.py` with a FastAPI app instance and lifespan that initialises `capture_engine` and `feedback_engine` without importing PyQt6
- [ ] 2.3 Implement `GET /health` returning `{"status": "ok", "version": __version__}`
- [ ] 2.4 Implement `POST /capture` — trigger `capture_engine.capture_once()`, return `{"frame_path": ..., "timestamp": ...}` or 422 if no window configured
- [ ] 2.5 Implement `POST /feedback` — accept optional `{"mode": "..."}` body, call `feedback_engine.run()`, return `{"mode", "feedback", "annotations"}` or 422 if no frames
- [ ] 2.6 Implement `GET /config` — return non-sensitive config fields (exclude `api_key`)
- [ ] 2.7 Implement `PUT /config` — update config fields in memory; persist to config file
- [ ] 2.8 Add env var overrides in `llm_config.py`: read `DRAWING_COACH_MODEL`, `DRAWING_COACH_API_KEY`, `DRAWING_COACH_API_BASE` and apply over file config
- [ ] 2.9 Update `__main__.py` entrypoint: if `--headless` flag or `DRAWING_COACH_HEADLESS=1`, start uvicorn on `DRAWING_COACH_PORT` (default 8080); else start GUI
- [ ] 2.10 Write integration tests for all four endpoints using FastAPI `TestClient` with mocked engine responses

## 3. PyInstaller Packaging

- [ ] 3.1 Create `drawing_coach.spec` PyInstaller spec file with `--onedir`, hidden imports for `pywin32`/`pyobjc`/`pynput`, and data files (icons, assets)
- [ ] 3.2 Add macOS `Info.plist` with `NSAccessibilityUsageDescription` and `NSScreenCaptureUsageDescription` entries; reference it in the spec file
- [ ] 3.3 Run `scripts/build_version.py` as a pre-build step in the spec file's `Analysis` block
- [ ] 3.4 Verify local build produces a working binary on at least one platform (smoke test: app launches, About dialog shows version)
- [ ] 3.5 Write `scripts/package.sh` (Linux/macOS) and `scripts/package.ps1` (Windows): run PyInstaller, zip output to `drawing-coach-<version>-<platform>.zip`

## 4. GitHub Actions — Binary Release Workflow

- [ ] 4.1 Create `.github/workflows/release.yml` triggered on `push: tags: ['v*']`
- [ ] 4.2 Add `build-binaries` job with matrix `os: [ubuntu-latest, windows-latest, macos-latest]`; each job runs `scripts/build_version.py` then the platform packaging script
- [ ] 4.3 Upload each zip as a workflow artifact using `actions/upload-artifact`
- [ ] 4.4 Add `create-release` job with `needs: build-binaries`; use `softprops/action-gh-release` to create the GitHub Release and attach all three zip artifacts
- [ ] 4.5 Add `publish-packages` job with `needs: create-release`; install `oras` via `oras-project/setup-oras` action; push each zip to `ghcr.io/<owner>/drawing-coach-binaries:<platform>-<version>`
- [ ] 4.6 Grant the workflow `packages: write` and `contents: write` permissions in the YAML

## 5. Dockerfile and Docker Workflow

- [ ] 5.1 Create `Dockerfile` with two stages: `builder` (install `.[server]` deps) and `runtime` (`python:3.12-slim`, copy installed packages, no PyQt6)
- [ ] 5.2 Set entrypoint to `python -m drawing_coach --headless`; expose port 8080
- [ ] 5.3 Create `.dockerignore` excluding `__pycache__`, `.git`, `tests/`, `*.spec`, platform-specific native libs not needed in the image
- [ ] 5.4 Verify image builds locally and `docker run -p 8080:8080` responds on `GET /health`
- [ ] 5.5 Verify `docker inspect` shows no PyQt6 in layers
- [ ] 5.6 Add `build-docker` job to `release.yml` triggered on `v*` tags; push `:<version>` and `:latest` tags to `ghcr.io`
- [ ] 5.7 Add separate `docker-main` workflow triggered on `push: branches: [main]`; push `:main` tag only
- [ ] 5.8 Use `docker/metadata-action` for tag generation and `docker/build-push-action` for build and push in both workflows

## 6. Documentation

- [ ] 6.1 Add "Installation" section to README with download links for each platform binary from GitHub Releases
- [ ] 6.2 Add "Docker" section to README: `docker run` quickstart, env var reference table (`DRAWING_COACH_MODEL`, `DRAWING_COACH_API_KEY`, `DRAWING_COACH_API_BASE`, `DRAWING_COACH_PORT`, `DRAWING_COACH_HEADLESS`)
- [ ] 6.3 Add "API Reference" section (or link to auto-generated `/docs` OpenAPI page) with endpoint descriptions and example curl commands
- [ ] 6.4 Document expected binary sizes per platform and macOS screen recording permission setup step
