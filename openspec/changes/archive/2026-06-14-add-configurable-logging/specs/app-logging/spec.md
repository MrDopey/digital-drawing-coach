## ADDED Requirements

### Requirement: Logging is configurable via env vars in .env
The system SHALL read `DRAWING_COACH_LOG_LEVEL`, `DRAWING_COACH_LOG_FILE`, and `DRAWING_COACH_LOG_MAX_BYTES` from the environment (populated by `.env` in the XDG config dir) and configure the Python `logging` hierarchy accordingly before any other module initialises.

`DRAWING_COACH_LOG_LEVEL` SHALL accept `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` (case-insensitive). Invalid values SHALL default to `WARNING` and emit a single warning to stderr. The default when unset SHALL be `WARNING`.

`DRAWING_COACH_LOG_FILE` SHALL accept an absolute or relative file path. When set, the system SHALL write log output to that file via a `RotatingFileHandler` in addition to stderr. When unset or empty, only stderr output is produced.

`DRAWING_COACH_LOG_MAX_BYTES` SHALL accept a positive integer specifying the maximum log file size in bytes. Default when unset: `10485760` (10 MB). When the file reaches this size the handler rotates with `backupCount=0` — the old content is discarded and a new file begins, ensuring total log file size never exceeds the configured cap. Invalid (non-integer or non-positive) values SHALL default to `10485760` and emit a WARNING to stderr.

#### Scenario: Log level set to INFO via .env
- **WHEN** `.env` contains `DRAWING_COACH_LOG_LEVEL=INFO`
- **THEN** the application logs INFO and above events across all modules from startup

#### Scenario: Log level is unset
- **WHEN** `DRAWING_COACH_LOG_LEVEL` is absent from the environment
- **THEN** the application defaults to WARNING level and produces no output during a normal successful run

#### Scenario: Invalid log level value
- **WHEN** `DRAWING_COACH_LOG_LEVEL=VERBOSE` (unrecognised value)
- **THEN** the system defaults to WARNING and emits a single stderr warning: `Unknown log level "VERBOSE", defaulting to WARNING`

#### Scenario: Log file path is set
- **WHEN** `DRAWING_COACH_LOG_FILE=/tmp/drawing-coach.log`
- **THEN** log output is written to that file via a RotatingFileHandler in addition to stderr

#### Scenario: Log file directory does not exist
- **WHEN** `DRAWING_COACH_LOG_FILE` points to a path whose parent directory does not exist
- **THEN** the system skips the file handler, logs a WARNING to stderr: `Cannot write log file at <path>: <reason>`, and continues with stderr-only logging

#### Scenario: Log file reaches the configured size cap
- **WHEN** the log file grows to `DRAWING_COACH_LOG_MAX_BYTES` bytes
- **THEN** the handler rotates: the current file is discarded and a new file begins at the same path, keeping total disk usage within the cap

#### Scenario: Custom size cap is configured
- **WHEN** `.env` contains `DRAWING_COACH_LOG_MAX_BYTES=5242880` (5 MB)
- **THEN** the RotatingFileHandler uses 5 MB as the rotation threshold

#### Scenario: Invalid size cap value
- **WHEN** `DRAWING_COACH_LOG_MAX_BYTES=abc` or `DRAWING_COACH_LOG_MAX_BYTES=0`
- **THEN** the system defaults to 10 MB and emits a WARNING to stderr: `Invalid DRAWING_COACH_LOG_MAX_BYTES "<value>", defaulting to 10485760`

### Requirement: Log messages use a consistent human-readable format
All log output SHALL use the format: `%(asctime)s %(levelname)s %(name)s — %(message)s`.

Module loggers SHALL follow the naming convention `drawing_coach.<module>` so they are controlled by the `drawing_coach` root logger.

#### Scenario: Log line format
- **WHEN** any log event is emitted
- **THEN** the output line contains timestamp, level, module path, and message in the defined format

### Requirement: App startup is logged
The system SHALL emit an INFO log at startup with the application version and a DEBUG log confirming the resolved log level and file destination.

#### Scenario: Application starts
- **WHEN** the application launches
- **THEN** an INFO line is logged: `Drawing Coach v<version> starting`

#### Scenario: Logging configuration is confirmed at DEBUG
- **WHEN** `DRAWING_COACH_LOG_LEVEL=DEBUG`
- **THEN** a DEBUG line is logged immediately after setup: `Log level=DEBUG file=<path or none>`
