## ADDED Requirements

### Requirement: Performance instrumentation is opt-in and inert by default

The system SHALL read `DRAWING_COACH_PERF_WATCHDOG` from the environment (populated by `.env` in the XDG config dir) and enable performance instrumentation only when it is set to a truthy value.

Accepted values SHALL be: unset, empty, `0`, `off`, `false` (disabled); `1`, `on`, `true` (watchdog and probes enabled); `full` (additionally arms the `faulthandler` fallback). Unrecognised values SHALL be treated as disabled and emit a single WARNING to stderr.

When disabled, the system SHALL NOT create a heartbeat timer, a watchdog thread, a GC callback, or a perf log handler, and every probe entry point SHALL short-circuit before allocating.

`DRAWING_COACH_PERF_STALL_MS` SHALL accept a positive integer specifying the stall threshold in milliseconds. Default when unset: `250`. Invalid values SHALL default to `250` and emit a WARNING to stderr.

#### Scenario: Watchdog is disabled by default
- **WHEN** `DRAWING_COACH_PERF_WATCHDOG` is absent from the environment
- **THEN** no watchdog thread, heartbeat timer, or GC callback is created, and no `PERF` lines are emitted

#### Scenario: Watchdog is enabled via .env
- **WHEN** `.env` contains `DRAWING_COACH_PERF_WATCHDOG=1`
- **THEN** the watchdog starts and emits a single `PERF-WATCHDOG-START` line recording the stall threshold, heartbeat interval, GUI thread identity, main thread identity, and process id

#### Scenario: Unrecognised watchdog value
- **WHEN** `DRAWING_COACH_PERF_WATCHDOG=yes-please`
- **THEN** instrumentation stays disabled and a single stderr warning is emitted naming the invalid value

#### Scenario: Custom stall threshold
- **WHEN** `.env` contains `DRAWING_COACH_PERF_STALL_MS=500`
- **THEN** only event-loop blockages of 500 ms or longer are reported as stalls

### Requirement: The system detects and reports GUI-thread stalls

When enabled, the system SHALL run a heartbeat timer on the Qt event loop that records a monotonic timestamp, and a daemon watchdog thread that reports a stall when that timestamp becomes older than the configured threshold.

The reported stall duration SHALL be measured as the interval between the last heartbeat before the stall and the first heartbeat after it, so it reflects the true blocked interval rather than the moment of detection.

The GUI thread SHALL be identified by the thread that executes the heartbeat callback, not by assuming it is the main thread. Both identities SHALL be logged at startup so a mismatch is visible.

#### Scenario: Event loop blocked beyond the threshold
- **WHEN** the Qt event loop is blocked for longer than the stall threshold
- **THEN** a `PERF-STALL-BEGIN` line is emitted with the elapsed time so far, a stall signature, and the sampled stack, followed by a `PERF-STALL-END` line reporting the total blocked duration

#### Scenario: Event loop is responsive
- **WHEN** the event loop services the heartbeat within the threshold
- **THEN** no stall lines are emitted

#### Scenario: Stall duration reflects the blocked interval
- **WHEN** the event loop is blocked for 1800 ms with a 250 ms threshold and a 100 ms heartbeat
- **THEN** the reported duration is the heartbeat-to-heartbeat gap of approximately 1800 ms, not the 250 ms detection latency

### Requirement: Stall reports identify what was executing

When a stall is detected, the system SHALL capture the GUI thread's Python stack via `sys._current_frames()` and include the deepest frames in the stall record, together with the top frames of every other live thread.

A stall record SHALL be tagged to indicate whether the watchdog thread was itself scheduled late. A late-sampled record SHALL be understood as evidence of a native, GIL-holding stall for which the duration is trustworthy but the stack is not.

Long stalls SHALL be re-sampled on an exponential backoff to a hard cap, so that a stall held inside a single blocking call is distinguishable from one progressing through a Python loop.

#### Scenario: Stall inside Python code
- **WHEN** the GUI thread stalls while executing Python
- **THEN** the record contains the deepest GUI-thread frames identifying the file, line, and function that entered the blocking work

#### Scenario: Stall inside Qt or platform code with no Python running
- **WHEN** the GUI thread stalls inside Qt event dispatch with no application Python frame on the stack
- **THEN** the record shows only the event-loop entry point, evidencing that no application Python code is responsible

#### Scenario: Watchdog thread starved by a GIL-holding call
- **WHEN** the watchdog thread's own iteration is delayed far beyond its poll interval
- **THEN** the record is tagged as late-sampled so the stack is not mistaken for the cause

#### Scenario: Long stall is re-sampled
- **WHEN** a stall persists well beyond the threshold
- **THEN** further samples are emitted on a backoff up to a fixed cap, each carrying its own stack

### Requirement: Stall reporting is bounded to avoid log flooding

The system SHALL emit at most one begin record and one end record per stall regardless of its duration, cap the number of continuation samples per stall, and collapse repeated stalls sharing a stack signature into a single counted line when the same signature was already reported in full recently.

Stall records SHALL be emitted as a single logging record with the stack embedded, so concurrent logging from other threads cannot interleave within a record.

#### Scenario: One stall produces one begin and one end
- **WHEN** a single stall lasts several seconds
- **THEN** exactly one `PERF-STALL-BEGIN` and one `PERF-STALL-END` line are emitted for it

#### Scenario: The same stall recurs
- **WHEN** a stall with an already-reported stack signature occurs again within the dedupe window
- **THEN** a single `PERF-STALL-REPEAT` line with a running count is emitted instead of a full stack block

#### Scenario: Concurrent logging during a stall report
- **WHEN** another thread logs while a stall record is being written
- **THEN** the stall record's stack lines remain contiguous because the record is emitted atomically

### Requirement: Scoped probes report the cost of suspect operations

The system SHALL provide a reusable scoped-timing helper usable as a context manager and as a decorator, which reports an elapsed duration, the executing thread's name, and caller-supplied fields.

Probes SHALL support nesting, where a nested probe folds its call count, total, and maximum into its enclosing probe rather than emitting its own line. Probes with no enclosing scope and a high call frequency SHALL be accumulated and flushed periodically as an aggregate carrying call count, total, and maximum for the window.

Probes SHALL be instrumented at: `HistoryPanel._render` (with frame and row counts), thumbnail generation, row-widget construction, row painting, hover hit-testing, `CaptureEngine._do_capture` split into window-rect lookup / image capture / duplicate comparison / PNG write, and the GUI-thread feedback-dedup hash computation.

#### Scenario: A panel render is timed
- **WHEN** the history panel rebuilds its rows with instrumentation enabled
- **THEN** a `PERF` line reports the elapsed milliseconds, the executing thread, the frame count, and the folded totals of its nested thumbnail and row-construction probes

#### Scenario: A capture cycle is timed by phase
- **WHEN** a capture completes with instrumentation enabled
- **THEN** a single `PERF` line reports total elapsed time plus separate figures for window-rect lookup, image capture, duplicate comparison, and PNG write, attributed to the capture thread

#### Scenario: High-frequency probes are aggregated
- **WHEN** row painting or hover hit-testing occurs hundreds of times within an aggregation window
- **THEN** one `PERF-AGG` line per label reports the window length, call count, total, and maximum, rather than one line per call

#### Scenario: Capture-thread and GUI-thread costs are distinguishable
- **WHEN** probes run concurrently on the capture thread and the GUI thread
- **THEN** each emitted line names its own thread and no nested probe folds into a scope opened on a different thread

### Requirement: Instrumentation reports live object and signal-receiver counts

The system SHALL track live instances of every modal dialog opened from the main window — `HistoryPanel`, `SettingsDialog`, `MemoryViewerDialog`, `ProgressPanel`, and `AppSelectionDialog` — without retaining them, reporting a per-class live count. It SHALL additionally report the number of receivers connected to the capture engine's `frames_changed` signal.

These counts SHALL appear on panel-render records, in the periodic liveness flush, and immediately after the history dialog's modal loop returns.

#### Scenario: Dialogs accumulate across reopens
- **WHEN** any tracked dialog has been opened and closed several times
- **THEN** the reported live instance count for that class reflects how many instances remain undeleted

#### Scenario: Subscribed panels remain connected after closing
- **WHEN** the history panel has been opened and closed several times
- **THEN** the reported `frames_changed` receiver count reflects how many closed panels are still subscribed and still re-rendering

#### Scenario: Instance tracking does not keep dialogs alive
- **WHEN** instrumentation is enabled and a tracked dialog is released
- **THEN** the tracking structure holds no strong reference that would prevent its collection

### Requirement: Garbage-collection pauses are reported

When enabled, the system SHALL observe garbage collection and report collections whose pause exceeds a fixed threshold, recording the generation, pause duration, objects collected, and the thread on which the collection ran.

#### Scenario: A long generation-2 collection occurs
- **WHEN** a generation-2 collection pauses the process beyond the reporting threshold
- **THEN** a `PERF-GC` line reports the generation, pause milliseconds, collected count, and the triggering thread

#### Scenario: Instrumentation is disabled
- **WHEN** `DRAWING_COACH_PERF_WATCHDOG` is not enabled
- **THEN** no GC callback is registered and no `PERF-GC` lines are emitted

### Requirement: A run summary is emitted at shutdown

The system SHALL emit a summary when the application is quitting, reporting uptime, total stall count, cumulative and maximum stall duration, the most frequent stall signatures, and per-label probe totals.

#### Scenario: Application quits after an instrumented run
- **WHEN** the application quits with instrumentation enabled
- **THEN** a single `PERF-SUMMARY` line reports uptime, stall count, cumulative and maximum stall milliseconds, top stall signatures, and per-label totals

### Requirement: Users can capture and share a perf snapshot

The Diagnostics dialog SHALL offer a "Copy Perf Snapshot" action that copies a plain-text summary — watchdog configuration, uptime, stall statistics, top stall signatures with their originating frames, live instance and receiver counts, per-label probe totals, and the perf log file path — to the clipboard.

The action SHALL be present only when instrumentation is enabled, so that normal runs are unaffected.

#### Scenario: Snapshot copied during an instrumented run
- **WHEN** the user opens Diagnostics with instrumentation enabled and activates "Copy Perf Snapshot"
- **THEN** the clipboard contains the plain-text summary including the perf log file path

#### Scenario: Diagnostics opened during a normal run
- **WHEN** the user opens Diagnostics with instrumentation disabled
- **THEN** the "Copy Perf Snapshot" action is not shown and the existing Copy Report behaviour is unchanged

### Requirement: A fallback traceback dumper is available for GIL-pinned stalls

When `DRAWING_COACH_PERF_WATCHDOG=full`, the system SHALL additionally arm `faulthandler` to dump tracebacks periodically to a separate file, without terminating the process.

This fallback exists because a native call that never releases the GIL prevents the Python watchdog thread from sampling. It SHALL NOT be armed at any other setting, and its output SHALL NOT be written to the application log.

#### Scenario: Full mode is requested
- **WHEN** `DRAWING_COACH_PERF_WATCHDOG=full`
- **THEN** `faulthandler` is armed to dump repeatedly to a dedicated file, the process is not terminated by it, and the file path is reported once at startup

#### Scenario: Standard mode is requested
- **WHEN** `DRAWING_COACH_PERF_WATCHDOG=1`
- **THEN** `faulthandler` is not armed and no dump file is created
