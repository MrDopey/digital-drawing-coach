## Context

The app is a Python + PyQt6 desktop application targeting Windows, macOS, and Linux. Currently it has no packaging or distribution pipeline — users would need to clone the repo and install dependencies manually. This change adds two distribution channels: (1) native binaries via PyInstaller for end-user installs, (2) a Docker image using a new headless HTTP API mode for programmatic/CI use. Both are published automatically on release tags via GitHub Actions.

## Goals / Non-Goals

**Goals:**
- Build and publish platform-native binaries on every `v*` tag push
- Publish binaries to GitHub Releases (as release assets) and register them as GitHub Packages (OCI artifacts via `oras`)
- Build and push a Docker image to `ghcr.io` on `v*` tags and `main` branch merges
- Headless API mode reuses existing engine modules — no duplication of core logic
- Version embedded at build time from the git tag

**Non-Goals:**
- macOS notarisation or Windows code signing (can be added later with certificates)
- Auto-update mechanism in the desktop app
- Homebrew formula, apt/deb, or other package manager integration
- ARM binary builds (amd64 only for now; Docker uses `linux/amd64`)

## Decisions

### Binary packaging: PyInstaller with one-dir mode

PyInstaller `--onedir` (not `--onefile`) is chosen because `--onefile` is noticeably slower to launch (decompresses to temp on every start) and causes false positives in some antivirus scanners. The output directory is zipped for upload. Each platform must build on its own native runner — PyInstaller cannot cross-compile.

Alternatives: `cx_Freeze` — less community support and worse PyQt6 compatibility. `Nuitka` — produces faster binaries but much longer build times unsuitable for CI. `Briefcase` — better installer UX (MSI, DMG) but higher complexity; viable future upgrade.

### GitHub Packages for binaries: OCI artifacts via `oras`

GitHub Packages supports OCI-compatible artifact storage beyond container images. `oras push` uploads the zipped binary as an OCI artifact to `ghcr.io/<owner>/<repo>-binaries:<platform>-<version>`. This is in addition to (not instead of) the GitHub Release asset upload, which remains the primary user-facing download path.

Alternatives: GitHub Releases only — sufficient for user downloads but doesn't satisfy the "GitHub Packages" requirement. npm/pip package — wrong package type for a binary.

### Headless mode: FastAPI + uvicorn

FastAPI is chosen over Flask for automatic OpenAPI docs generation (useful for CI integrations) and native async support (important for non-blocking screenshot capture). The server is a thin HTTP wrapper — it calls the same `capture_engine`, `feedback_engine`, and `llm_config` modules used by the GUI.

Three endpoints:
- `GET /health` — returns `{version, status}`
- `POST /capture` — triggers a manual screenshot capture, returns frame path
- `POST /feedback` — triggers LLM feedback on the latest capture, returns feedback text (and annotation JSON in overlay mode)
- `GET/PUT /config` — read or update LLM config fields

Headless mode starts when the app is launched with `--headless` flag or as the Docker entrypoint. No display server required.

Alternatives: gRPC — overkill for this use case. WebSockets — unnecessary for request/response feedback pattern.

### Docker image: multi-stage, headless only

```
Stage 1 (builder): python:3.12-slim — install deps, copy source
Stage 2 (runtime): python:3.12-slim — copy installed packages, set entrypoint
```

The GUI (PyQt6) is NOT installed in the Docker image — it's excluded via the `[server]` extras group. This keeps the image small (~400 MB vs ~900 MB with Qt). Screen capture in Docker uses `mss` with `DISPLAY` env var or virtual framebuffer — for headless API use the capture target is typically a remote URL or base64 image POSTed directly to `/feedback`, bypassing the window-capture flow entirely.

LLM config is supplied via environment variables (`DRAWING_COACH_MODEL`, `DRAWING_COACH_API_KEY`, `DRAWING_COACH_API_BASE`) which override the config file — standard 12-factor pattern for containers.

### CI workflow: matrix build on tag push

```yaml
on:
  push:
    tags: ['v*']

jobs:
  build-binaries:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
  
  build-docker:
    runs-on: ubuntu-latest
    needs: build-binaries
```

Docker build depends on the binaries job completing successfully (acts as a gate). Release creation happens in a separate `release` job that collects all binary artifacts and creates the GitHub Release.

### Version embedding

`pyproject.toml` version is the source of truth. A `build_version.py` script (run by PyInstaller spec file and Docker build) writes `src/_version.py` from the `GITHUB_REF_NAME` env var (the tag) at build time. The GUI About dialog and API `/health` endpoint both read from `_version.py`.

## Risks / Trade-offs

- **PyInstaller + pynput on macOS**: accessibility permissions required for global hotkeys; bundled apps may need extra entitlements in `Info.plist` → Mitigation: include a pre-built `Info.plist` in the PyInstaller spec with `NSAccessibilityUsageDescription`
- **PyInstaller + pywin32 on Windows**: some `win32gui` hooks need explicit PyInstaller `--hidden-import` flags → Mitigation: document known hidden imports in `drawing_coach.spec`
- **Docker screen capture**: `mss` requires a display; headless Docker containers have no display → Mitigation: document that `/capture` endpoint requires `DISPLAY` or Xvfb in Docker; for pure API use, clients POST images directly to `/feedback` without using the capture flow
- **Binary size**: PyInstaller + numpy + Pillow + LiteLLM produces ~250–400 MB bundles → Mitigation: acceptable for a desktop app; document expected sizes in README
- **`oras` availability in CI**: `oras` must be installed on runners → Mitigation: use the official `oras-project/setup-oras` GitHub Action
