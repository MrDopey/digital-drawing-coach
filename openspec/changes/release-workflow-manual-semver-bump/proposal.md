## Why

The release workflow currently triggers on pushing a `v*` tag, and additionally publishes every binary a second time as an OCI artifact to GHCR via `oras` — a secondary distribution channel nobody has asked to consume, that adds a third-party action (`oras-project/setup-oras`) and an extra job for no confirmed benefit. We want a simpler, fully manual release flow: a maintainer triggers the release from the Actions tab, picks a semver bump size, and the workflow builds, releases, and then bumps-and-commits the version back to `main` itself — so `main` never needs a human to hand-edit a version number, and its checked-in version always reads as a preview of the next release.

## What Changes

- **BREAKING**: Release trigger changes from `push: tags: ["v*"]` to `workflow_dispatch` with one required input, `bump`, a choice of `patch` / `minor` / `major`. Pushing a `v*` tag no longer starts a release on its own.
- **BREAKING**: Drop OCI/`oras` publishing entirely — remove the `publish-packages` job and the `oras-project/setup-oras` dependency. Binaries are only distributed as GitHub Release assets.
- The application's version now lives in one authoritative place, `pyproject.toml`'s `[project] version`, and must always be a valid semver (`MAJOR.MINOR.PATCH`). This replaces deriving the version from the pushed git tag (`GITHUB_REF_NAME`).
- The release workflow now, in order: builds the three platform binaries embedding the **current** committed version, creates the GitHub Release tagged `v<current-version>` with those binaries attached, then computes the next version per the chosen bump, writes it back to `pyproject.toml`, and commits + pushes that bump directly to `main`.
- Because the bump-and-commit happens after the release is cut, `main`'s `pyproject.toml` version is always one bump ahead of the last shipped release — a "preview" of what the next release will be numbered, until it is itself released and bumped again.
- Workflow steps are pinned to well-known, high-adoption GitHub Actions (`actions/checkout`, `actions/setup-python`, `actions/upload-artifact`, `actions/download-artifact`) plus the official `gh` CLI (preinstalled on GitHub-hosted runners, authenticated via `GITHUB_TOKEN`) for creating the release, and plain `git`/Python for the version bump and commit — no third-party action is used anywhere in the workflow.
- The tray icon menu's "About" entry and About dialog no longer show a bare `dev` label when running an unbuilt copy from source. They now show `pyproject.toml`'s current version with a `-prerelease` suffix (e.g. `0.2.0-prerelease`) — since `main`'s committed version is always a preview of the next release, this makes that visible in the app itself rather than the display collapsing to an uninformative `dev`.
- Release notes generation adapts to whether PRs were actually used: if any PRs were merged since the previous release, `gh release create --generate-notes` produces the usual PR-grouped changelog; if none were merged (commits landed directly on `main`, which is this project's normal flow), the workflow falls back to a bullet list built from `git log <prev-tag>..HEAD` commit subjects instead of the otherwise-empty PR-based body.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `binary-release`: trigger changes from tag-push to `workflow_dispatch` with a bump-type input; version is sourced from `pyproject.toml` (required to be semver) instead of the pushed tag; the OCI/GitHub-Packages publishing requirement is removed; a new requirement covers the post-release version bump and commit-back-to-main behavior; the unbuilt/from-source version display changes from a bare `dev` label to `<pyproject-version>-prerelease`.

## Impact

- `.github/workflows/release.yml`: trigger, job graph, and permissions change; `publish-packages` job removed.
- `scripts/build_version.py`: reads the version from `pyproject.toml` instead of `GITHUB_REF_NAME`.
- `src/drawing_coach/_version.py`: the unbuilt/committed fallback stops being the literal string `"dev"` and instead resolves to `pyproject.toml`'s current version plus a `-prerelease` suffix at import time; a real release build still overwrites this file with the concrete released version string, as today.
- `src/drawing_coach/main_window.py`: no code change expected beyond what falls out of `_version.py`'s new value — the tray menu "About" entry and About dialog already read `__version__` from that module.
- `scripts/package.sh` / `scripts/package.ps1`: drop their own `GITHUB_REF_NAME`-based version derivation now that `build_version.py` is the single place version is resolved.
- New `scripts/bump_version.py` (or equivalent): applies a patch/minor/major bump to `pyproject.toml`'s version.
- `pyproject.toml`: version becomes a maintained, semver-enforced field bumped only by the release workflow (not expected to be hand-edited).
- `openspec/specs/binary-release/spec.md`: requirements updated per above.
- `openspec/specs/docker-distribution/spec.md`: out of scope for this change — its Docker build job was already removed from `release.yml` in a prior commit (`e229bc7`) without the spec being updated, so it is already stale independent of this change. Left untouched here; flagged in design.md as a pre-existing drift worth a separate cleanup.
