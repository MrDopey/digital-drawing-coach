## Why

The Session History window is sluggish on macOS — several seconds of lag on hover, scroll and click, reported as present **on the very first open** of the panel. Four fixes have been attempted (see `.tmp/histor-latency-progress.md`); every one was validated only on Linux/Xvfb, and every one failed or was reverted. The cost of this bug so far is entirely the absence of a measurement channel to the one machine that reproduces it.

Two of the leading hypotheses have now been ruled out by arithmetic and by the user's own report — the confirmed `HistoryPanel` instance leak cannot explain a first-open symptom, and per-row hit-testing was measured at 0.02 ms/event. Rather than attempt a fifth blind fix, this change ships opt-in instrumentation that runs on the user's Mac and produces a log identifying what actually blocks the GUI thread.

## What Changes

- New `drawing_coach.perf` module providing:
  - A **GUI-thread stall watchdog** — a heartbeat `QTimer` on the event loop plus a daemon thread that detects a stale heartbeat, samples the GUI thread's Python stack via `sys._current_frames()`, and logs stall duration + stack. Records are tagged when the watchdog itself was scheduled late, which distinguishes a Python-level stall from a native GIL-holding one.
  - **Scoped timing probes** — a reusable context manager/decorator placed at coarse boundaries (`HistoryPanel._render`, `_pil_to_pixmap`, `CaptureEngine._do_capture` split by phase, `MainWindow._update_request_dedup_state`), with high-frequency sites (`paintEvent`, hover hit-test) aggregated over a time window instead of logged per event.
  - **Live-instance and signal-receiver counts**, so the log states how many `HistoryPanel` objects exist and how many receivers `frames_changed` has.
  - A **GC pause probe**, since ~50 full-size PIL images are resident in `CaptureEngine`'s buffer and a long gen-2 collection is a plausible whole-app freeze.
- New env var `DRAWING_COACH_PERF_WATCHDOG` (`off` by default, `1`/`on` enables, `full` additionally arms `faulthandler` as a fallback for GIL-pinned stalls) and `DRAWING_COACH_PERF_STALL_MS` to tune the threshold.
- Logging carve-out: the `drawing_coach.perf` child logger is set to `DEBUG` when the watchdog is enabled while the `drawing_coach` root stays at its configured level, so perf output flows without making litellm/urllib3 noisy. Stalls and any probe over 100 ms escalate to `WARNING` so they appear at the default level.
- A **"Copy Perf Snapshot"** button in the existing Diagnostics dialog, visible only when the watchdog is on, reusing the established `Copy Report` support path.
- Documentation: README env table rows, a Troubleshooting recipe for reporting a sluggish UI, and `.env.example` entries.

This change deliberately contains **no fix** for the sluggishness. The four separately-confirmed defects found during investigation (HistoryPanel instance leak, `_render()` full teardown/rebuild, thumbnail cost, GUI-thread SHA-256 hashing per capture) are recorded in the design document as follow-up work, to be prioritised by what the instrumented log shows.

## Capabilities

### New Capabilities
- `perf-diagnostics`: opt-in GUI-thread stall detection, scoped timing probes, live-instance/receiver counts, GC pause reporting, and a user-copyable perf snapshot.

### Modified Capabilities
- `app-logging`: adds the `DRAWING_COACH_PERF_WATCHDOG` / `DRAWING_COACH_PERF_STALL_MS` environment variables and the `drawing_coach.perf` child-logger level carve-out to the logging configuration contract.

## Impact

- **New**: `src/drawing_coach/perf.py`, `tests/test_perf.py`.
- **Modified**: `src/drawing_coach/env.py` (two readers), `src/drawing_coach/logging_config.py` (perf logger level + auto file destination), `src/drawing_coach/__main__.py` (install watchdog, summary on `aboutToQuit`), `src/drawing_coach/history_panel.py`, `src/drawing_coach/capture_engine.py`, `src/drawing_coach/main_window.py` (probe call sites only — no behaviour change), `src/drawing_coach/diagnostics.py` (snapshot button), `README.md`, `.env.example`.
- **Dependencies**: none added. Uses only `sys`, `threading`, `traceback`, `gc`, `weakref`, `faulthandler` from the stdlib.
- **Runtime cost when disabled**: one env read at import, a `WeakSet.add` per `HistoryPanel`, and no-op context managers at coarse boundaries. No timer, no thread, no GC callback, no handler is created.
- **Risk**: instrumentation placed in the very code under suspicion could itself perturb timings. Mitigated by call-site `if perf.ON:` guards on hot paths and by aggregating high-frequency probes.
