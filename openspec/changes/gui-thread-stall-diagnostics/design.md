## Context

The Session History window is sluggish on macOS — several seconds of lag on hover, scroll and click. Four attempted fixes are recorded in `.tmp/histor-latency-progress.md` (not in git; it lives in the primary checkout):

| # | Change | Result |
|---|---|---|
| 1 | Viewport mouse-move tracking + `itemAt()` hit-testing instead of Enter/Leave on the row widget | Did not fix the paint bug; kept |
| 2 | `WA_StyledBackground` on `_FrameRowWidget` | Fixed the paint bug, **introduced** the latency |
| 3 (`58e62f9`) | Removed the stylesheet; hover background painted directly in `paintEvent()` | Hover works; latency not resolved |
| 4 (reverted) | Cached row thumbnails + `Image.reduce()` downscale | Latency not resolved on macOS despite a large measured win on Linux |

Every attempt was verified only under Linux/Xvfb, which reproduces neither macOS-native style nor its compositor. That is the actual failure mode of this investigation, and it is what this change addresses.

### What investigation has established

Verified by running code against the real classes:

- **Every parented modal dialog leaks.** All five follow `dlg = X(..., self); dlg.exec()` with no `WA_DeleteOnClose`, `deleteLater()`, or `closeEvent`, so C++ parent ownership retains each one after the Python name goes out of scope. Measured over three open/close cycles each:

  | Dialog | Live after 3 opens | Recurring work | Retains |
  |---|---|---|---|
  | `HistoryPanel` | 3 | **3 `_render()` per `frames_changed`** | up to 50 full-size frames |
  | `SettingsDialog` | 3 | none | config + hotkey refs (small) |
  | `MemoryViewerDialog` | 3 | none | tree text (small) |
  | `ProgressPanel` | 3 | none | small |
  | `AppSelectionDialog` | 3 | none | window list (small) |

  `DiagnosticsDialog` is parented to `SettingsDialog`, so it leaks only transitively; its `closeEvent` does shut down its executor and coordinator thread. `SessionPickerDialog` is constructed with `parent=None` from `__main__`, so Python GC reclaims it.

  Only `HistoryPanel` connects to a signal on an object that outlives it (`self._engine.frames_changed.connect(self._render)`, `history_panel.py:169`), which is why it is the only one that leaks *recurring work* rather than just bytes.

- **A stale `HistoryPanel` pins full-size frames across a session switch.** `_add_row` stores a strong reference via `item.setData(Qt.ItemDataRole.UserRole, frame)`, and `new_session()` / `load_session()` mutate the buffer **without emitting `frames_changed`** (verified — the signal is emitted only at `capture_engine.py:111` and `:340`). So a leaked panel never re-renders on a session switch and keeps holding the previous session's frames. Measured: 3/3 frames stayed alive after the engine dropped them. At `BUFFER_SIZE = 50` and ~4.5 MB per frame at macOS nominal resolution, that is ~220 MB pinned per stale panel — and memory pressure is itself a credible whole-app-stall mechanism, independent of any per-row cost.
- **`_update_request_dedup_state` blocks the GUI thread on every capture.** `main_window.py:484-493` computes `sha256(frame.image.tobytes())` per selected frame. Measured at 5120×2880: 41 ms per frame, ~104 ms per capture at the default `lookback_frames=2`. This happens **with the history panel closed** — the only known cost that does.
- **The progress document's "200× from `Image.reduce()`" is wrong.** Re-measured at 5120×2880 → 48 px: `copy()+thumbnail()` 12.2 ms vs `reduce()+thumbnail()` 8.0 ms — **1.5×, not 200×**. The 200× came entirely from attempt 4's cache (skipping the work), not from `reduce()`. This misattribution would have misled the next attempt.
- **Hit-testing is not the problem.** 200 viewport mouse-moves cost 3 ms total (0.02 ms/event). Retired.

### What rules out the leading hypothesis

The user reports the lag is present **on the very first open of the panel**. A first open has exactly one live panel, so the instance leak — the largest confirmed defect — cannot be the primary cause. Combined with macOS capturing at *nominal* (point) resolution rather than Retina backing-store pixels (`_backend_macos.py` passes `kCGWindowImageNominalResolution`), a ~1500×1000 capture makes a 50-row rebuild roughly 100 ms, an order of magnitude short of "several seconds".

So the dominant cost is somewhere no one has measured. The remaining candidates — Qt/AppKit-level stalls with no Python running, `paintEvent` on 50 `setItemWidget()` children under macOS-native style, the capture thread's PNG encode and CoreGraphics round-trips contending for the GIL, and generation-2 GC pauses over a heap holding ~50 full-size PIL images — are not distinguishable by reasoning. They are trivially distinguishable by one stall record from the user's Mac.

## Goals / Non-Goals

**Goals:**

- Produce, from a run on the user's own Mac, a log that names what blocks the GUI thread — including the case where the answer is "no application Python code at all".
- Distinguish GUI-thread cost from capture-thread cost, and Python-level stalls from native GIL-holding ones.
- Cost effectively nothing when disabled, so it can ship permanently rather than being re-invented at the next platform-specific report.
- Require one line of setup from the user and produce one artefact to send back.

**Non-Goals:**

- **Fixing the sluggishness.** This change contains no fix. Shipping a fix alongside the instrument would make the next measurement uninterpretable, which is the exact trap the previous four attempts fell into.
- Reverting attempts 2 and 3 (`9e90864`, `58e62f9`). The `paintEvent()`-based hover painting is what makes the hover background paint on macOS at all.
- A sampling profiler or flame graph. The question is "what blocks the event loop", not "where is CPU spent".
- Reducing capture memory or changing capture resolution.

## Decisions

### D1 — A Python heartbeat watchdog, with `faulthandler` as a gated fallback

A `QTimer` on the GUI thread updates a monotonic timestamp; a daemon thread notices when that timestamp goes stale and samples `sys._current_frames()[gui_ident]`.

*Why not `faulthandler.dump_traceback_later` as the primary?* It writes raw text to a bare fd, bypassing the formatter, rotation and timestamps, so it interleaves unparseably with the log; it cannot report a measured stall duration, only "N seconds after I was armed"; it has no stall start/end concept so it cannot dedupe or summarise; and keeping it armed only during stalls means cancel+re-arm ten times a second.

*Why keep it at all?* It is the one mechanism that survives a native call holding the GIL, because it dumps from a C thread. Gated behind `DRAWING_COACH_PERF_WATCHDOG=full`, writing to a separate file. Ask the user for it only if standard mode reports long stalls with useless stacks.

### D2 — Identify the GUI thread from the heartbeat, not by assuming it is the main thread

The heartbeat callback records `threading.get_ident()` on every tick. That is authoritative by construction: the callback runs on the thread owning the timer, which is the thread running the event loop. Both the GUI-thread and main-thread identities are logged at startup so a mismatch is visible rather than silently wrong.

### D3 — Measure stall duration heartbeat-to-heartbeat

Duration is the gap between the last beat before the stall and the first beat after it — the true blocked interval, ±one heartbeat. Reporting "how stale the timestamp was when I noticed" would understate short stalls and depend on the poll interval.

### D4 — Treat a late-scheduled watchdog iteration as a finding, not a failure

If the GUI thread is inside a native call that never releases the GIL, the watchdog thread cannot run and cannot sample; when it finally does, it sees whatever runs *after* the stall. The watchdog therefore records whether its own iteration was delayed far beyond its poll interval and tags the record. **A late-sampled record is itself the diagnosis**: it means a native, GIL-holding stall, which retires every Python-level hypothesis at once. Trust the duration, distrust the stack, on those records.

### D5 — A stack bottoming out in C++ is still decisive

The frame captured is the exact Python callsite that entered C++ and did not return, which separates every open hypothesis in one line:

| Deepest frame | Reading |
|---|---|
| `history_panel.py` `setItemWidget` | the rebuild path |
| `history_panel.py` `QPainter(self)` in `paintEvent` | macOS-native paint cost on `setItemWidget()` children |
| `main_window.py` `sha256(frame.image.tobytes())` | the GUI-thread dedup hashing |
| `__main__.py` `app.exec()` with nothing above it | **no application Python is running** — the stall is inside Qt/AppKit/compositor |

That last row is the finding no amount of Linux benchmarking could ever produce, and it is a plausible outcome given attempt 2's symptom appeared the moment Qt's CSS engine was involved.

### D6 — Nested probes fold; high-frequency probes aggregate

A thread-local stack of open probes lets a nested probe add its count/total/max into its parent instead of emitting a line. Probes with no enclosing scope and a high call rate (`paintEvent`, hover hit-test) accumulate into a process-wide bucket flushed on a fixed window.

Thread-local is load-bearing, not incidental: capture-thread and GUI-thread numbers must never mix, because *which thread pays* is precisely the open question. Aggregating paints is also load-bearing — repaint **frequency** is as diagnostic as duration, and a repaint storm would never show up in a single timing while per-event lines would be unreadable.

### D7 — Route perf output through a child logger at `DEBUG`, escalating slow records to `WARNING`

`logging_config.py:50-67` attaches handlers to the `drawing_coach` logger with no handler level, and ancestor logger levels are not re-checked during propagation. So setting only `drawing_coach.perf` to `DEBUG` emits perf output through the existing handlers while the root stays at `WARNING`. The user gets full perf output and litellm/urllib3 stay quiet.

Escalating stalls and any probe ≥100 ms to `WARNING` means the user does not have to set `DRAWING_COACH_LOG_LEVEL=DEBUG` at all — one env var, not two, and a log that stays small.

### D8 — Auto-create the perf log file when no log file is configured

If `DRAWING_COACH_LOG_FILE` is unset, attach a rotating handler under the XDG data dir (alongside the existing `debug_log_dir()`). This removes a step from the user's instructions and, importantly, makes the instrumentation work unchanged if the app is later run as a packaged `.app` launched from Finder, where stderr goes nowhere. `setup_logging()` already calls `load_dotenv()` on the XDG `.env` at `logging_config.py:20`, so the `.env` toggle works in both launch modes.

### D9 — Ship permanently, off by default

The entire cost of this bug is the absence of a measurement channel to a machine the developer does not have. Deleting the channel after this diagnosis guarantees rebuilding it at the next platform-specific report — and this project's developer and user are on different operating systems, so there will be a next time. `DiagnosticsDialog` already exists on exactly this rationale.

Two qualifications: hot call sites get an `if perf.ON:` guard at the *callsite* so that when disabled there is not even an object construction — instrumentation must not become the performance bug it exists to find. And `faulthandler` never arms outside `full`.

### D10 — Make the watchdog clock-injectable and its core synchronous

`StallWatchdog(clock=...)` plus a public single-iteration `check_once()` makes stall detection testable deterministically with no sleeps. The daemon thread is a two-line `while: check_once(); sleep(poll)` wrapper — untested by design; everything of substance lives in `check_once()`.

### D11 — Track instances with a `WeakSet`, receivers with `QObject.receivers()`

`perf.track(self)` costs about a microsecond and holds no strong reference, so it can run unconditionally. It is called from the `__init__` of all five leaking dialogs — `HistoryPanel`, `SettingsDialog`, `MemoryViewerDialog`, `ProgressPanel`, `AppSelectionDialog` — keyed by class name, so the log states which panels actually accumulate on the user's machine rather than assuming it matches what was measured here.

`engine.receivers(engine.frames_changed)` is verified working in PyQt6 and is the direct measurement of how many `_render` subscriptions are live. Reported on every render record, in the periodic flush, and after `_open_history`'s `exec()` returns.

A `WeakSet` count can lag one GC cycle; the periodic flush accepts that, the on-demand snapshot forces a `gc.collect()` first.

### D12 — Include a GC pause probe

`CaptureEngine.BUFFER_SIZE = 50` full-size PIL images are resident — 220 MB at 1512×982, more at larger window sizes. A long generation-2 collection over that heap is a credible whole-app freeze that matches "several seconds, whole window, first open" better than any per-row cost, and it is three lines to rule in or out via `gc.callbacks`.

## Risks / Trade-offs

- **The instrumentation perturbs the thing it measures** → `if perf.ON:` guards at hot callsites; aggregate high-frequency probes over a window; coarse boundaries only. If `PERF-AGG` volume ever becomes the bottleneck, the fix is a `QueueHandler`/`QueueListener` pair — do not add it pre-emptively.
- **File logging is synchronous on the calling thread**, so a probe on the capture thread pays for its own write → keep to a few lines per second by construction; the 5 s aggregation window is the main lever.
- **A GIL-pinned stall defeats the Python sampler** → detected and tagged (D4), with `full` mode's `faulthandler` as the escape hatch.
- **The log may show nothing conclusive** — e.g. stalls with no Python frames and no late-sample tag. That is still progress: it eliminates the entire Python-level hypothesis space and redirects the next step to Qt/AppKit (widget count, `setItemWidget` cost, native style). The follow-up would be a minimal standalone PyQt6 reproducer run on the Mac, not more changes to this codebase.
- **`sys._current_frames()` is private API** → stable across CPython 3.x in practice; used read-only; may need a type-ignore for the checker.
- **`filterwarnings = ["error"]` in `pyproject.toml`** → `weakref`/`gc` usage must emit no warnings, and the `gc.callbacks` entry must be removed on test teardown.
- **Tests import `main_window.py` → `pynput`**, which probes for a real X connection at import even under `QT_QPA_PLATFORM=offscreen` → run with `xvfb-run -a uv run pytest`.

## Migration Plan

No data migration; the feature is additive and disabled by default. Rollback is setting the env var back to unset, or reverting the change wholesale — no persisted state is written except the perf log file.

**Measurement protocol** (the actual deliverable of this change):

1. User runs from source with the watchdog on and the history panel exercised — open it, hover, scroll, click, and stay open across at least two captures (default interval 30 s).
2. A **second run with the history panel never opened**, held for several captures. This answers the one discriminating question the investigation has never had an answer to: does the app stall with the panel closed? A yes points at the capture thread or the GUI-thread dedup hashing; a no confines it to the panel.
3. Both logs plus a Copy Perf Snapshot come back; the next change is written against them.

**Zero-code control worth running alongside**: check out `a80c520^` (the commit before the hover feature landed) and see whether the sluggishness reproduces. If it does, all four attempts have been chasing a pre-existing problem.

## Follow-up work (deliberately excluded from this change)

Confirmed defects found during investigation, each real independently of the reported symptom, to be prioritised by what the logs show:

1. **Modal dialog leak (all five)** — fix with `deleteLater()` after `exec()` returns at each call site, plus a `done()` override in `HistoryPanel` that disconnects `frames_changed` so the panel is structurally incapable of background work regardless of whether a call site remembers. Call sites that read the dialog after `exec()` (`main_window.py:581`, `settings_dialog.py:256`) must capture the values *before* deleting.

   **Not** `WA_DeleteOnClose`: measured, it destroys the C++ object during `exec()`'s unwinding, so the first statement after `dlg.exec()` raises `RuntimeError: wrapped C/C++ object ... has been deleted` — which would break exactly those two call sites.

   `HistoryPanel` is the load-bearing one (recurring `_render()` work plus ~220 MB of pinned frames per stale panel); the other four are bytes-only and fixed for consistency. A regression test must use `qtbot.wait(...)` and not `processEvents()` — measured, `processEvents()` does not flush `DeferredDelete` outside a running event loop, so the test would falsely fail.

   Separately, `new_session()` / `load_session()` should emit `frames_changed`; not doing so is what lets a stale panel pin a whole previous session, and it also means a *legitimately open* panel silently goes stale on a session switch.
2. **`_render()` full teardown/rebuild** — diff rows against the engine's frame list instead of `clear()`+rebuild. Beyond cost, the rebuild drops hover, selection and scroll position out from under a user mid-interaction every 30 s, which is a genuine "feels janky" symptom no benchmark would show. Note `QListWidget` defaults to `ScrollPerItem`, so the scrollbar value is an item index and inserting at the top shifts content — anchor on frame identity.
3. **GUI-thread SHA-256 per capture** — memoise the digest on `CapturedFrame` and warm it on the capture thread. Must stay byte-identical to `sha256(image.tobytes())`: persisted `feedback.json` entries are keyed on it.
4. **Thumbnail cost** — `Image.reduce()` fast path and dropping the caller's redundant second `.scaled(48, 48, ...)`. Genuinely minor (1.5×); no cache needed if (2) lands.

Also correct `.tmp/histor-latency-progress.md`'s "200×" attribution so it does not mislead a future attempt.

## Open Questions

- Does the app stall with the history panel closed? Resolved by step 2 of the measurement protocol, not by discussion.
- Does the sluggishness predate the hover feature (`a80c520`)? Resolved by the zero-code control above.
- What are the actual capture dimensions on the user's Mac? `_write_frame` already debug-logs `(%dx%d)`, so the instrumented run answers this for free.
