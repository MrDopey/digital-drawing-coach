## ADDED Requirements

### Requirement: Docker image is published to GitHub Container Registry on release and main
The system SHALL build and push a Docker image to `ghcr.io/<owner>/drawing-coach` on every `v*` tag push and on every merge to `main`. Tagged releases SHALL produce both a version tag (e.g. `:v1.2.0`) and the `:latest` tag. Merges to `main` SHALL produce a `:main` tag only.

#### Scenario: Release tag triggers image publish
- **WHEN** a `v*` tag is pushed
- **THEN** the Docker image is built and pushed with both `:<version>` and `:latest` tags

#### Scenario: Merge to main triggers image publish
- **WHEN** a commit is merged to the `main` branch (not a tag)
- **THEN** the Docker image is built and pushed with the `:main` tag only; `:latest` is not updated

#### Scenario: Image is visible in GitHub Packages
- **WHEN** a user browses the repository's Packages page
- **THEN** the `drawing-coach` container image appears with available tags listed

### Requirement: Docker image runs in headless API mode
The system SHALL configure the Docker image entrypoint to start the application in headless API mode. The GUI and PyQt6 SHALL NOT be included in the image.

#### Scenario: Container starts and serves health endpoint
- **WHEN** the Docker image is run with `docker run -p 8080:8080 ghcr.io/<owner>/drawing-coach`
- **THEN** the container starts and `GET http://localhost:8080/health` returns HTTP 200

#### Scenario: Container requires no display
- **WHEN** the container is run without `DISPLAY` set and without an X server available
- **THEN** the container starts successfully without errors related to display initialisation

### Requirement: LLM configuration is supplied via environment variables in Docker
The system SHALL read `DRAWING_COACH_MODEL`, `DRAWING_COACH_API_KEY`, and `DRAWING_COACH_API_BASE` from the container environment and use them for all LLM calls, overriding any mounted config file.

#### Scenario: LLM config supplied via environment
- **WHEN** the container is started with `-e DRAWING_COACH_MODEL=gpt-4o -e DRAWING_COACH_API_KEY=sk-...`
- **THEN** all feedback requests use that model and key without requiring a mounted config file

#### Scenario: No LLM environment variables set
- **WHEN** the container starts without LLM environment variables and no config file is mounted
- **THEN** `POST /feedback` returns `{"error": "No LLM configured"}` with HTTP 422; the container does not crash on startup

### Requirement: Docker image is multi-stage and minimal
The system SHALL use a multi-stage Dockerfile. The final image SHALL be based on `python:3.12-slim` and SHALL NOT include PyQt6, build tools, or test dependencies.

#### Scenario: Image size is within bounds
- **WHEN** the image is built and inspected
- **THEN** the compressed image size SHALL be under 600 MB

#### Scenario: Image does not contain PyQt6
- **WHEN** the image layers are inspected
- **THEN** no PyQt6 or Qt shared libraries are present in the final stage

### Requirement: Server port is configurable via environment variable
The system SHALL read `DRAWING_COACH_PORT` from the environment to set the HTTP server port (default: 8080).

#### Scenario: Custom port is used
- **WHEN** the container is started with `-e DRAWING_COACH_PORT=9000 -p 9000:9000`
- **THEN** the server listens on port 9000 and health checks on that port succeed
