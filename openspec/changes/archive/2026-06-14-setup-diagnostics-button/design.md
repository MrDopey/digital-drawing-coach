## Context

Drawing Coach requires three independent systems to work together before any coaching feedback can flow: OS screen capture permissions, a reachable vision LLM, and writable storage for config and session data. Currently failures in any of these produce silent hangs or opaque runtime errors. The settings dialog has a "Test Connection" button for the LLM alone, but nothing surfaces the other failure points.

The app already has platform-specific backend modules (`_backend_macos.py`, `_backend_linux.py`, `_backend_windows.py`) that abstract OS differences. The capture engine uses `mss` for screenshots. Secrets and config live under XDG paths resolved by `paths.py`.

## Goals / Non-Goals

**Goals:**
- Single "Run Diagnostics" entry point that exercises all critical subsystems
- Per-check pass/fail status with a human-readable message and an actionable remediation hint on failure
- Platform-aware: checks adapt to macOS vs. Linux vs. Windows
- Non-blocking UI: checks run in parallel background threads; dialog remains responsive and fast checks resolve immediately without waiting for the LLM
- No new runtime dependencies

**Non-Goals:**
- Automatically fixing detected problems (e.g. requesting OS permission on behalf of the user)
- Replacing the existing "Test Connection" button in the LLM tab — that stays for quick iteration
- Diagnosing network latency or LLM response quality
- Automated test/CI integration (this is a human-facing widget)

## Decisions

### 1 — New `diagnostics.py` module, not inline in `settings_dialog.py`

Each check function (`check_screen_capture`, `check_llm`, `check_config_path`, `check_sessions_dir`) returns a `CheckResult(name, passed, message, hint)` dataclass. The `DiagnosticsDialog` widget imports these functions and a `run_all_checks(config)` convenience wrapper.

**Rationale:** Keeps check logic unit-testable without instantiating Qt widgets. Alternative (inline methods on `SettingsDialog`) would make the checks untestable and mix concerns.

### 2 — Non-modal `QDialog` opened from a "Diagnostics…" button in `SettingsDialog`

The dialog has a scrollable list of check rows (icon + name + message) and a "Re-run" button. It is non-modal (`show()` not `exec_()`).

**Rationale:** Users need to act on hints while the dialog is visible — e.g. opening macOS System Settings, then switching back to re-run. A modal dialog would block that workflow. Alternative (inline results panel inside SettingsDialog) would clutter the existing tab layout.

### 3 — `ThreadPoolExecutor` for parallel check execution, results marshalled via a single coordinator `QThread`

All checks are submitted concurrently to a `concurrent.futures.ThreadPoolExecutor`. A single coordinator `QThread` iterates `as_completed()` and emits a `check_done(CheckResult)` signal for each result as it arrives. The coordinator emits `all_done()` once the executor drains. The dialog rows are pre-rendered in a fixed display order; each row updates in-place when its result arrives.

**Rationale:** The checks are fully independent — none depends on another's result. Most complete in <5 ms; the LLM call takes 1–5 s. Sequential execution wastes that time by blocking fast checks behind the slow one. With parallel execution, total wall-clock time = slowest single check (LLM) rather than the sum. A coordinator `QThread` is used rather than emitting Qt signals directly from executor threads, because cross-thread signal emission from arbitrary `threading.Thread`s requires care; the coordinator isolates that concern.

**Alternative considered:** One `QThread` per check — avoids the coordinator but creates up to eight threads per run and makes teardown (cancel-on-close) more complex. `ThreadPoolExecutor` + one coordinator is simpler to reason about and cheaper.

### 4 — macOS screen capture check via `CGWindowListCopyWindowInfo`

On macOS, `mss` silently returns a black screenshot when Screen Recording permission is denied, making it useless as a capability probe. Instead, call `CGWindowListCopyWindowInfo(kCGWindowListOptionAll, kCGNullWindowID)` via `ctypes` (already used in `_backend_macos.py`). An empty result list means permission is denied.

**Rationale:** This is the same heuristic used by tools like `scrcpy` and `obs-studio`. Alternative (try-capture-and-compare-to-black) is fragile because a legitimately black screen would false-positive.

On Linux, attempt `mss().grab(mss().monitors[0])` and catch any exception — a success means capture works.

On Windows, `mss` works without special permission; perform a grab as the check.

### 5 — macOS Input Monitoring check via `AXIsProcessTrustedWithOptions`

On macOS, `pynput` needs Input Monitoring permission to register global hotkeys. `hotkey_manager.py:42` silently catches the resulting exception so the hotkey simply never fires. Check using `ctypes` to call `AXIsProcessTrustedWithOptions(NULL)` from the Accessibility framework — returns `True` when trusted. This is the same API checked by accessibility tools.

**Rationale:** There is no public API specific to Input Monitoring; `AXIsProcessTrustedWithOptions` is the closest proxy and reflects the same system permission gate that blocks pynput.

### 6 — Linux xdotool check via `shutil.which`

On Linux, `_backend_linux.py` wraps `xdotool` for window enumeration and raises `FileNotFoundError` when the binary is missing — caught silently, resulting in an empty window list. Check with `shutil.which("xdotool") is not None`.

**Rationale:** A subprocess probe (`xdotool version`) is more expensive than `which` and provides no additional signal for a first-run check.

### 7 — Config JSON integrity check via `json.loads`

Read `config_path()` if it exists and attempt `json.loads()`. A `JSONDecodeError` means the file is corrupt and all settings will silently fall back to defaults on next launch.

**Rationale:** The existing config dir write check doesn't catch an already-corrupt file. This is a cheap read-only probe with high diagnostic value.

### 8 — Pillow PNG codec check via in-memory encode

Call `Image.new("RGB", (1, 1)).save(io.BytesIO(), "PNG")`. If this raises, Pillow's PNG support is broken and captured frames will be silently dropped by `capture_engine.py:250`.

**Rationale:** An in-memory encode is faster than writing to disk and catches the codec issue without side effects.

### 9 — Config and sessions directory checks use `os.access` + write probe

Check config dir: `os.access(config_path().parent, os.W_OK)`. Check sessions dir: create the directory if absent (`mkdir(parents=True, exist_ok=True)`), then write and delete a probe file.

**Rationale:** `os.access` is sufficient for config (we just need to know if saves will work). For sessions we also want to verify the dir can be created if missing, so the mkdir+probe is more complete. Alternative (just check existence) misses the "dir exists but is read-only" case.

## Risks / Trade-offs

- **macOS API volatility** → `CGWindowListCopyWindowInfo` is a stable, public API used since macOS 10.5; low risk of removal
- **LLM check costs a real API call** → The call sends a single "hi" message (identical to the existing Test Connection), which costs ~1 token; acceptable. Hint text will note this.
- **Non-modal dialog lifetime** → If user closes SettingsDialog while DiagnosticsDialog is open, the parent reference becomes invalid. Mitigation: set `DiagnosticsDialog` parent to `main_window`, not `settings_dialog`.
- **Executor teardown on close** → If the user closes the dialog while checks are running, the executor must be shut down cleanly. Mitigation: call `executor.shutdown(wait=False, cancel_futures=True)` in `closeEvent` before stopping the coordinator thread.
- **False-pass on LLM check** → A successful "hi" completion doesn't guarantee the vision endpoint works (some providers have separate vision quotas). The check message will say "text completion succeeded" to be honest about scope.

## Migration Plan

No data migration required. The feature is purely additive:
1. Add `diagnostics.py`
2. Patch `settings_dialog.py` to add a "Diagnostics…" button
3. Patch `_backend_macos.py` to expose the window-list helper
4. Ship as a normal release; no config schema changes

## Open Questions

- Should the "Diagnostics…" button also appear in the main window toolbar (not just inside Settings)? Leaning **yes** — users may not know to look in Settings. Deferring to implementation based on UI review.
