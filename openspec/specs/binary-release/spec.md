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

### Requirement: Native binaries are built on every release tag
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

### Requirement: Binaries are zipped and named by platform and version
The system SHALL produce a zip archive for each platform named `drawing-coach-<version>-<platform>.zip` (e.g. `drawing-coach-v1.2.0-windows.zip`). Each zip SHALL contain the full PyInstaller output directory.

#### Scenario: Binary archive is correctly named
- **WHEN** a build job completes on a given platform
- **THEN** the output zip file contains the platform identifier (`windows`, `macos`, `linux`) and the release tag version

#### Scenario: Archive is uploaded to GitHub Release
- **WHEN** the release creation job runs
- **THEN** all three zip archives are attached as downloadable assets to the GitHub Release

### Requirement: Binaries are published as GitHub Packages (OCI artifacts)
The system SHALL push each platform binary as an OCI artifact to GitHub Container Registry using `oras`, at `ghcr.io/<owner>/<repo>-binaries:<platform>-<version>` (e.g. `ghcr.io/org/drawing-coach-binaries:windows-v1.2.0`).

#### Scenario: OCI artifact is pushed after release creation
- **WHEN** the release creation job completes
- **THEN** three `oras push` commands run — one per platform — uploading the zip as an OCI artifact layer

#### Scenario: OCI artifact is listed in GitHub Packages
- **WHEN** a user browses the repository's Packages page
- **THEN** each platform binary appears as a versioned package entry

### Requirement: Version is embedded in the binary at build time
The system SHALL embed the release tag as the application version in the binary at build time. The embedded version SHALL be displayed in the app's About dialog and returned by the API `/health` endpoint.

#### Scenario: Binary reports correct version
- **WHEN** a binary built from tag `v1.2.0` is launched
- **THEN** the About dialog displays version `1.2.0`

#### Scenario: Development build shows dev version
- **WHEN** the app is run directly from source without a tag
- **THEN** the version displays as `dev`

