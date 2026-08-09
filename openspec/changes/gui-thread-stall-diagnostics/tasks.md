## 1. Core perf module (no app wiring — testable standalone)

- [x] 1.1 Create `src/drawing_coach/perf.py` with the module-level enable flag (`ON`), thresholds, and an `init(raw_watchdog, raw_stall_ms) -> bool` that parses the env values, validates them, and warns to stderr on invalid input. Import `PyQt6.QtCore` lazily inside `install_watchdog()` only, so the module stays importable from `capture_engine.py`.
- [x] 1.2 Implement the scoped probe: a `Probe` class usable via `probe(label, *, child=False, **fields)` as a context manager and `timed(label, **fields)` as a decorator, with a `set(**fields)` for values only known inside the block, and a no-op singleton returned when disabled.
- [x] 1.3 Implement probe nesting via a `threading.local()` stack — nested probes fold count/total/max into the enclosing probe on the *same* thread; parentless high-frequency probes accumulate into a process-wide bucket. Every emitted line carries the executing thread's name.
- [x] 1.4 Implement the periodic aggregate flush (`PERF-AGG`) with a fixed window, reporting label, window length, call count, total, and maximum.
- [x] 1.5 Implement `StallWatchdog` with an injectable clock, `beat()`, and a synchronous `check_once()` holding the begin/sample/end state machine. Record the GUI thread ident from `beat()`. Measure stall duration heartbeat-to-heartbeat.
- [x] 1.6 Add stack sampling to `check_once()`: `sys._current_frames()` for the GUI thread (deepest frames) plus the top frames of other live threads; tag the record when the watchdog's own iteration ran late.
- [x] 1.7 Add spam control: one begin + one end per stall, capped continuation samples on exponential backoff, and signature-based dedupe emitting `PERF-STALL-REPEAT` with a count. Emit each stall record as a single logging record with the stack embedded.
- [x] 1.8 Escalate stall records and any probe at or above the slow threshold from `DEBUG` to `WARNING`.
- [x] 1.9 Implement `track()`/`instance_count()` over per-class `WeakSet`s, `signal_receivers(obj, signal)` via `QObject.receivers`, and the periodic `PERF-LIVE` flush reporting every tracked class with a non-zero count.
- [x] 1.10 Implement the GC pause probe via `gc.callbacks`, reporting generation, pause ms, collected count, and triggering thread above a fixed threshold. Provide an uninstall path for test teardown.
- [x] 1.11 Implement `install_watchdog()` (heartbeat `QTimer` with a module-level reference so it is not collected, watchdog thread start, `PERF-WATCHDOG-START` line), `log_summary()` (`PERF-SUMMARY`), and `snapshot() -> str` (forces `gc.collect()` first).
- [x] 1.12 Implement the `full`-mode `faulthandler` arming to a dedicated file with `repeat=True` and no process termination; never armed at any other setting.
- [x] 1.13 Write `tests/test_perf.py`: probe nesting and folding, cross-thread isolation, aggregate flush, disabled-mode no-ops and no allocations, stall detection driven by a fake clock through `check_once()`, duration measured heartbeat-to-heartbeat, late-sample tagging, spam caps and signature dedupe, `WeakSet` not retaining tracked objects, and GC callback removal on teardown.

## 2. Environment and logging wiring

- [x] 2.1 Add `perf_watchdog()` and `perf_stall_ms()` readers to `src/drawing_coach/env.py`, matching the existing reader style.
- [x] 2.2 Add the corresponding cases to `tests/test_env.py`, mirroring the existing per-variable test pairs.
- [x] 2.3 Wire `perf.init()` into `setup_logging()` in `src/drawing_coach/logging_config.py` after handlers are attached; on enable, set only the `drawing_coach.perf` child logger to `DEBUG`.
- [x] 2.4 When enabled and `DRAWING_COACH_LOG_FILE` is unset, attach a rotating perf log handler under the XDG data dir honouring `DRAWING_COACH_LOG_MAX_BYTES`, and report the resolved path once at startup.
- [x] 2.5 Add logging-config tests: `drawing_coach.perf` at `DEBUG` while `drawing_coach` stays at `WARNING`; auto file handler appears only when no log file is configured; nothing changes when disabled.
- [x] 2.6 Install the watchdog in `src/drawing_coach/__main__.py` immediately after `QApplication` construction and before the session picker, and connect `perf.log_summary` to `app.aboutToQuit`.

## 3. Probe call sites (no behaviour change)

- [x] 3.1 `src/drawing_coach/history_panel.py`: probe `_render` (fields: frame count, row count, live panel count, receiver count), `_pil_to_pixmap` (child, with pixel dimensions), `_FrameRowWidget.__init__` (child), and `_update_lookback_indicator` (child).
- [x] 3.2 `src/drawing_coach/history_panel.py`: probe `_FrameRowWidget.paintEvent` and the `eventFilter` mouse-move hit-test as parentless aggregated probes, each behind an `if perf.ON:` callsite guard.
- [x] 3.3 Call `perf.track(self)` in the `__init__` of all five leaking dialogs — `HistoryPanel`, `SettingsDialog`, `MemoryViewerDialog`, `ProgressPanel`, `AppSelectionDialog` — so the log reports per-class live counts.
- [x] 3.4 `src/drawing_coach/capture_engine.py`: wrap `_do_capture` in a parent probe with child scopes for `get_window_rect`, `capture_image`, `_compute_mae`, the PNG write in `_write_frame`, and the `frames_changed` emit; parent fields carry pixel dimensions, MAE, and whether the frame was stored.
- [x] 3.5 `src/drawing_coach/main_window.py`: probe `_update_request_dedup_state` (field: mode) and `_current_frame_hashes` (child; fields: frame count and total bytes hashed).
- [x] 3.6 `src/drawing_coach/main_window.py`: emit the `PERF-OPEN` record after `_open_history`'s `dlg.exec()` returns, reporting live panel count and `frames_changed` receiver count.
- [x] 3.7 Add a regression test that `HistoryPanel` and `CaptureEngine` behave identically with `perf.ON` both false and true, and that no probe changes any observable result.

## 4. User-facing snapshot affordance

- [x] 4.1 Add a "Copy Perf Snapshot" `QPushButton` to the existing button row in `src/drawing_coach/diagnostics.py`, visible only when `perf.ON`, wired to copy `perf.snapshot()` to the clipboard following the existing `_copy_report` pattern.
- [x] 4.2 Add tests mirroring the existing Copy Report tests: button hidden when instrumentation is disabled, and clipboard contents include the log path and stall statistics when enabled.
- [x] 4.3 Confirm `tests/test_design_system_compliance.py` still passes — the new button must be a plain `QPushButton` with no stylesheet or hex literal.

## 5. Documentation

- [ ] 5.1 Add `DRAWING_COACH_PERF_WATCHDOG` and `DRAWING_COACH_PERF_STALL_MS` rows to the README environment-variable table, and matching commented entries in `.env.example`.
- [ ] 5.2 Add a README Troubleshooting subsection, "Reporting a sluggish or frozen UI", giving the exact `uv run` command with the env var, where the log lands, and what to send back.
- [ ] 5.3 Correct `.tmp/histor-latency-progress.md` in the primary checkout: the "200× speedup from `Image.reduce()`" is a misattribution — `reduce()` is ~1.5×, and the 200× came from attempt 4's cache. Record the confirmed `HistoryPanel` leak, the measured GUI-thread hashing cost, and that the first-open symptom rules the leak out as the primary cause.

## 6. Verification and measurement

- [ ] 6.1 Run `xvfb-run -a uv run pytest` with the full suite green, plus one pass with `DRAWING_COACH_PERF_WATCHDOG=1` set to confirm instrumentation does not break existing tests.
- [ ] 6.2 Confirm the disabled path allocates nothing: assert no watchdog thread, no heartbeat timer, no GC callback, and no perf handler exist after `setup_logging()` with the variable unset.
- [ ] 6.3 Hand the user the measurement protocol: run 1 with the history panel opened and exercised across at least two captures; run 2 with the panel never opened, held for several captures. Collect both logs and a Copy Perf Snapshot.
- [ ] 6.4 Suggest the zero-code control alongside: check out `a80c520^` and check whether the sluggishness reproduces before the hover feature existed.
- [ ] 6.5 Read the returned logs and write the follow-up change against them. Do not land any fix from the design's follow-up list before this step.
