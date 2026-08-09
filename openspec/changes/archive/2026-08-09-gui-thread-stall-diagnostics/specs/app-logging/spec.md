## ADDED Requirements

### Requirement: Performance logging is routed without raising the global log level

When performance instrumentation is enabled, the system SHALL set the `drawing_coach.perf` child logger to `DEBUG` while leaving the `drawing_coach` root logger at its configured level, so that performance output is emitted without increasing verbosity for any other module or third-party library.

Performance records whose measured duration reaches or exceeds 100 ms, and all stall records, SHALL be emitted at `WARNING` so they are visible at the default log level without any change to `DRAWING_COACH_LOG_LEVEL`.

When instrumentation is enabled and `DRAWING_COACH_LOG_FILE` is unset, the system SHALL additionally attach a rotating file handler writing to a default performance log path under the XDG data directory, and SHALL report that path once at startup. The existing `DRAWING_COACH_LOG_MAX_BYTES` cap SHALL apply to it.

#### Scenario: Perf logging enabled with default log level
- **WHEN** `DRAWING_COACH_PERF_WATCHDOG=1` and `DRAWING_COACH_LOG_LEVEL` is unset
- **THEN** the `drawing_coach` logger remains at `WARNING`, the `drawing_coach.perf` logger is at `DEBUG`, and stalls plus operations of 100 ms or longer are still recorded

#### Scenario: Third-party verbosity is unaffected
- **WHEN** performance instrumentation is enabled
- **THEN** loggers outside the `drawing_coach.perf` hierarchy retain the level configured by `DRAWING_COACH_LOG_LEVEL`

#### Scenario: No log file configured
- **WHEN** performance instrumentation is enabled and `DRAWING_COACH_LOG_FILE` is unset
- **THEN** a rotating performance log file is created under the XDG data directory and its path is reported at startup

#### Scenario: A log file is already configured
- **WHEN** performance instrumentation is enabled and `DRAWING_COACH_LOG_FILE` is set
- **THEN** performance output goes to that configured file and no additional performance log file is created

#### Scenario: Instrumentation disabled
- **WHEN** `DRAWING_COACH_PERF_WATCHDOG` is not enabled
- **THEN** no performance logger level is altered and no performance log handler is attached

## MODIFIED Requirements

### Requirement: Logging is configurable via env vars in .env
The system SHALL read `DRAWING_COACH_LOG_LEVEL`, `DRAWING_COACH_LOG_FILE`, `DRAWING_COACH_LOG_MAX_BYTES`, `DRAWING_COACH_PERF_WATCHDOG`, and `DRAWING_COACH_PERF_STALL_MS` from the environment (populated by `.env` in the XDG config dir) and configure the Python `logging` hierarchy accordingly before any other module initialises.

`DRAWING_COACH_LOG_LEVEL` SHALL accept `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` (case-insensitive). Invalid values SHALL default to `WARNING` and emit a single warning to stderr. The default when unset SHALL be `WARNING`.

`DRAWING_COACH_LOG_FILE` SHALL accept an absolute or relative file path. When set, the system SHALL write log output to that file via a `RotatingFileHandler` in addition to stderr. When unset or empty, only stderr output is produced.

`DRAWING_COACH_LOG_MAX_BYTES` SHALL accept a positive integer specifying the maximum log file size in bytes. Default when unset: `10485760` (10 MB). When the file reaches this size the handler rotates with `backupCount=0` — the old content is discarded and a new file begins, ensuring total log file size never exceeds the configured cap. Invalid (non-integer or non-positive) values SHALL default to `10485760` and emit a WARNING to stderr.

`DRAWING_COACH_PERF_WATCHDOG` SHALL enable opt-in performance instrumentation. It is disabled when unset, empty, `0`, `off`, or `false`; enabled by `1`, `on`, or `true`; and `full` additionally arms the `faulthandler` fallback. Unrecognised values SHALL be treated as disabled and emit a single WARNING to stderr.

`DRAWING_COACH_PERF_STALL_MS` SHALL accept a positive integer specifying the GUI-thread stall threshold in milliseconds. Default when unset: `250`. Invalid values SHALL default to `250` and emit a WARNING to stderr.

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

#### Scenario: Performance watchdog enabled via .env
- **WHEN** `.env` contains `DRAWING_COACH_PERF_WATCHDOG=1`
- **THEN** performance instrumentation is enabled at startup, before any other module initialises

#### Scenario: Performance watchdog left unset
- **WHEN** `DRAWING_COACH_PERF_WATCHDOG` is absent from the environment
- **THEN** performance instrumentation stays disabled and logging behaves exactly as before this change

#### Scenario: Invalid stall threshold value
- **WHEN** `DRAWING_COACH_PERF_STALL_MS=abc` or `DRAWING_COACH_PERF_STALL_MS=0`
- **THEN** the system defaults to 250 ms and emits a WARNING to stderr
