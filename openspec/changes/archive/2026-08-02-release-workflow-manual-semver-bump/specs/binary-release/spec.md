## ADDED Requirements

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

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Native binaries are built on every release tag
**Reason**: Releases are no longer triggered by pushing a git tag. The version now lives in `pyproject.toml`, not the tag, so a pushed tag no longer carries the information needed to start a release; releases are dispatched manually instead. Replaced by "Release is triggered manually via workflow_dispatch with a version-bump input".
**Migration**: Trigger a release by running the "Release" workflow from the Actions tab (or `gh workflow run release.yml -f bump=patch`), selecting a bump size, instead of pushing a `v*` tag.

The system SHALL build platform-native binaries for Windows (`.exe` bundle), macOS (`.app` bundle), and Linux (binary directory) using PyInstaller when a `v*` tag is pushed to the repository. Each platform SHALL be built on its own native CI runner. Builds for all three platforms SHALL complete before a GitHub Release is created.

#### Scenario: Release tag is pushed
- **WHEN** a tag matching `v*` is pushed to the repository
- **THEN** the CI pipeline starts three parallel build jobs — one each for `ubuntu-latest`, `windows-latest`, and `macos-latest`

#### Scenario: All platform builds succeed
- **WHEN** all three platform build jobs complete successfully
- **THEN** a GitHub Release is created for the tag with the three binary archives attached as release assets

#### Scenario: One platform build fails
- **WHEN** any platform build job fails
- **THEN** the GitHub Release is NOT created and the CI pipeline reports failure

### Requirement: Binaries are published as GitHub Packages (OCI artifacts)
**Reason**: Nothing consumes the GHCR/OCI copy of the binaries; the GitHub Release remains the sole intended distribution path. Removing this also drops the `oras-project/setup-oras` third-party action dependency, keeping the workflow's action set limited to well-known, high-adoption actions.
**Migration**: Download binaries from the GitHub Release page (`drawing-coach-<version>-<platform>.zip`) instead of pulling `ghcr.io/<owner>/drawing-coach-binaries`.

The system SHALL push each platform binary as an OCI artifact to GitHub Container Registry using `oras`, at `ghcr.io/<owner>/<repo>-binaries:<platform>-<version>` (e.g. `ghcr.io/org/drawing-coach-binaries:windows-v1.2.0`).

#### Scenario: OCI artifact is pushed after release creation
- **WHEN** the release creation job completes
- **THEN** three `oras push` commands run — one per platform — uploading the zip as an OCI artifact layer

#### Scenario: OCI artifact is listed in GitHub Packages
- **WHEN** a user browses the repository's Packages page
- **THEN** each platform binary appears as a versioned package entry
