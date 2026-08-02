# binary-release Specification

## Purpose
TBD - created by archiving change drawing-coach-distribution. Update Purpose after archive.
## Requirements
### Requirement: Minimum platform OS versions
The system SHALL require macOS 10.15 (Catalina) or later on Apple platforms. The macOS binary SHALL NOT be expected to run on earlier macOS versions. This floor exists because the Input Monitoring permission check uses `IOHIDCheckAccess`, which was introduced in macOS 10.15.

#### Scenario: macOS binary runs on Catalina or later
- **WHEN** the macOS binary is launched on macOS 10.15 or later
- **THEN** the app starts and all permission checks function correctly

#### Scenario: macOS binary on pre-Catalina is unsupported
- **WHEN** the macOS binary is launched on macOS 10.14 or earlier
- **THEN** behaviour is undefined and the version is not supported

---

### Requirement: Release is triggered manually via workflow_dispatch with a version-bump input
The system SHALL trigger the release workflow only via `workflow_dispatch`, requiring a single input `bump` constrained to the choices `patch`, `minor`, or `major`. Pushing a git tag SHALL NOT by itself start a release build.

#### Scenario: Maintainer dispatches a release
- **WHEN** a maintainer runs the "Release" workflow from the Actions tab (or `gh workflow run`) and selects a `bump` value of `patch`, `minor`, or `major`
- **THEN** the CI pipeline starts three parallel build jobs — one each for `ubuntu-latest`, `windows-latest`, and `macos-latest` — using the version currently committed in `pyproject.toml`

#### Scenario: Tag push alone does not trigger a release
- **WHEN** a tag matching `v*` is pushed to the repository without a corresponding `workflow_dispatch` run
- **THEN** no release build starts

### Requirement: Version is bumped and committed back to main after release
After the GitHub Release is successfully created, the system SHALL compute the next version by applying the `bump` input (`patch`, `minor`, or `major`) to the version that was just released, write that next version into `pyproject.toml`, and commit and push that change directly to `main`. This SHALL result in `main`'s committed version always being one bump ahead of the last released version — a preview of the next release.

#### Scenario: Patch bump after release
- **WHEN** a release is dispatched with `bump: patch` while the released version was `1.2.0`
- **THEN** `pyproject.toml` on `main` is updated to `version = "1.2.1"` and that change is committed and pushed to `main`

#### Scenario: Minor bump resets patch
- **WHEN** a release is dispatched with `bump: minor` while the released version was `1.2.3`
- **THEN** `pyproject.toml` on `main` is updated to `version = "1.3.0"`

#### Scenario: Major bump resets minor and patch
- **WHEN** a release is dispatched with `bump: major` while the released version was `1.2.3`
- **THEN** `pyproject.toml` on `main` is updated to `version = "2.0.0"`

#### Scenario: Bump commit happens only after release succeeds
- **WHEN** any platform build job or the release-creation job fails
- **THEN** no version bump is computed or committed, and `pyproject.toml` on `main` is left unchanged

### Requirement: Binaries are zipped and named by platform and version
The system SHALL produce a zip archive for each platform named `drawing-coach-<version>-<platform>.zip` (e.g. `drawing-coach-v1.2.0-windows.zip`). Each zip SHALL contain the full PyInstaller output directory.

#### Scenario: Binary archive is correctly named
- **WHEN** a build job completes on a given platform
- **THEN** the output zip file contains the platform identifier (`windows`, `macos`, `linux`) and the release tag version

#### Scenario: Archive is uploaded to GitHub Release
- **WHEN** the release creation job runs
- **THEN** all three zip archives are attached as downloadable assets to the GitHub Release

### Requirement: Version is embedded in the binary at build time
The system SHALL read the application version from `pyproject.toml`'s `[project].version` field, which SHALL always hold a valid semantic version (`MAJOR.MINOR.PATCH`), and embed it in the binary at build time. This value SHALL also be used to compute the release tag (`v<version>`). The embedded version SHALL be displayed in the tray icon menu's About entry and About dialog.

#### Scenario: Binary reports the committed version
- **WHEN** a binary is built by the release workflow while `pyproject.toml` has `version = "1.2.0"`
- **THEN** the built binary's About dialog displays version `1.2.0` and the release is tagged `v1.2.0`

#### Scenario: Unbuilt source run shows the previewed version with a prerelease suffix
- **WHEN** the app is run directly from source without going through the release workflow's build step, and `pyproject.toml` currently has `version = "1.3.0"`
- **THEN** the tray icon menu's About entry and About dialog display the version as `1.3.0-prerelease`

#### Scenario: Unbuilt source run falls back to dev when pyproject.toml is unavailable
- **WHEN** the app is run from an installed copy with no `pyproject.toml` present alongside the source (e.g. a non-editable wheel install) and without going through the release workflow's build step
- **THEN** the version displays as `dev`
