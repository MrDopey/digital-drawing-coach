## Context

`MainWindow` (`src/drawing_coach/main_window.py`) owns `_pause_btn` (QPushButton) and `_tray_pause_action` (QAction), both wired to `_toggle_pause()`. Enabled state is never touched today — both widgets are always enabled from construction. `_update_status()` sets label text from `self._capture.paused` but has no concept of "no target selected." `CaptureEngine.target` (`capture_engine.py`) is `None` until `set_target()` is called from `_open_app_selection()`, and is not cleared when the window is lost (`_on_window_lost()` calls `pause()` but leaves `target` set to the stale, now-invalid window).

## Goals / Non-Goals

**Goals:**
- Pause/Resume control (button + tray action) is disabled and shows the paused-state label ("Resume") whenever `CaptureEngine.target` is `None`.
- Control becomes enabled as soon as a window is successfully selected.
- Control returns to the disabled/paused-label state when the target is lost.

**Non-Goals:**
- No change to `CaptureEngine.pause()`/`resume()` semantics or the underlying capture loop.
- No change to how windows are enumerated or selected (`AppSelectionDialog`, `WindowManager`).

## Decisions

- **Single source of truth: `_update_status()`.** Rather than adding enable/disable calls at every call site, drive `setEnabled(self._capture.target is not None)` from inside `_update_status()`, which already runs on every relevant transition (frame captured, window lost, session switch, app selection, manual toggle). This avoids missed call sites and matches the existing pattern of `_update_status()` being the single place that reconciles button text.
- **No `target` clearing needed.** Considered clearing `CaptureEngine._target` in `_on_window_lost()` so "no target" and "target lost" are the same state. Rejected: `CaptureEngine.target` is used elsewhere (e.g. `_update_status()`'s "Monitoring: <title>" label, `_capture_loop`'s rect lookup) and changing its lifecycle is out of scope for a UI-only fix. Instead, track "usable target" in the UI layer as `self._capture.target is not None`, which is already `None` until first selection; window-loss handling already calls `pause()`, and disabling the button on a stale target is a display-only concern — the worst case if this reasoning is wrong is the button stays enabled after loss, which the disable-on-`_on_window_lost` call below handles explicitly regardless of `target`'s value.
- **Explicit disable in `_on_window_lost()`.** Even though `_update_status()` is called from there, add `self._pause_btn.setEnabled(False)` (via `_update_status()`) so the disabled state doesn't depend on `target` being falsy specifically at that moment — belt-and-suspenders since `target` isn't cleared on loss.
- **Initial state set in `_build_ui()`.** Call `_update_status()` once at the end of `_build_ui()` (or explicitly `setEnabled(False)` on the two widgets at construction) so the disabled state is correct before any capture activity occurs, rather than relying on the first `frame_captured` signal.

## Risks / Trade-offs

- [Risk] `target` is non-`None` but stale after window loss, so `target is not None` alone would say "enabled" right after loss. → Mitigation: `_on_window_lost()` explicitly forces the disabled state rather than relying solely on the `target` check.
- [Risk] Missing a call site that changes `target` without calling `_update_status()`. → Mitigation: grep confirms `set_target()` is only called from `_open_app_selection()`, which already calls `_update_status()` immediately after.
