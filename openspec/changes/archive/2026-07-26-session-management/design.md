## Context

Sessions are currently managed entirely inside `CaptureEngine`: on first frame capture it either resumes the most recent session (if < 24 h old) or creates a new one. The user has no visibility into this decision and no ability to name, browse, or switch sessions. `meta.json` today contains only `start_time` and `end_time`. Frame PNGs already exist under `sessions/<id>/frames/` so thumbnail generation is free.

## Goals / Non-Goals

**Goals:**
- Session picker dialog shown on launch (skipped when 0 sessions exist)
- Editable session names persisted in `meta.json`
- In-app session switching via a Sessions menu
- Active session name in the main window title bar

**Non-Goals:**
- Exporting or archiving sessions
- Merging or duplicating sessions
- Changing the on-disk session storage format beyond adding `name` to `meta.json`
- Cloud sync or multi-device

## Decisions

### 1. Session picker is a separate dialog, shown before `MainWindow` opens

The picker is invoked in `__main__.py` before `MainWindow` is constructed. It returns one of three outcomes: `resume(session_dir)`, `new`, or `quit`. This keeps `MainWindow` unaware of session selection logic.

**Alternative considered:** show picker inside `MainWindow` on startup — rejected because it requires `MainWindow` to be in an indeterminate "no session loaded" state.

### 2. `CaptureEngine` gains `load_session(path)` and `new_session()` methods

Rather than gutting `_init_session`, we add two explicit public methods the caller (picker + Sessions menu) can invoke. `_init_session` becomes a thin wrapper that delegates to whichever path is appropriate.

**Alternative:** pass `session_dir` as a constructor arg — rejected because in-app switching requires re-loading without reconstructing the engine.

### 3. Thumbnail = last PNG in `frames/`, loaded at picker open time

No separate thumbnail file. `SessionPickerDialog` reads `sessions_dir()` at open time, sorts frame PNGs, and loads the last one as a 120×80 `QPixmap`. Hover expands to 360×240 via a `QToolTip` with an HTML `<img>` tag (or a floating `QLabel`).

**Alternative:** write a `thumbnail.png` on frame capture — more robust for very long sessions but adds write overhead; deferred to future iteration.

### 4. `meta.json` gains `name: str` (optional, defaults to `YYYY-MM-dd-HH-mm-ss | <drawing_app>`)

Reading code uses `meta.get("name") or default_name(start_time, drawing_app)`, where `default_name` formats the start time as `YYYY-MM-dd-HH-mm-ss` and appends ` | <drawing_app>` when a target application was set (omitted otherwise). Writing happens on session create and on explicit rename. Backward-compatible — old sessions without `name` show the derived default label.

### 5. Sessions menu in `MainWindow` toolbar / menu bar

A `Sessions` menu (menu bar) lists: current session name (greyed, non-clickable), separator, all other sessions by name (newest first), separator, `New Session`. Selecting one calls `CaptureEngine.load_session(path)` and updates the title bar.

**Alternative:** floating panel or sidebar — heavier UI; menu is sufficient for v1.

## Risks / Trade-offs

- [Picker adds startup latency] → thumbnail loading is deferred; only meta.json is read on picker open; frames loaded lazily on hover
- [Race between session switch and active capture] → `CaptureEngine.load_session` stops the capture timer, flushes, then switches; restarts timer after load
- [Picker shown every launch even for power users] → mitigated by "skip when 0 sessions" rule; future option to suppress if desired

## Migration Plan

1. Deploy: existing sessions gain no `name` field — picker displays the derived default label, which is equivalent to today's behaviour.
2. Rollback: removing `name` from `meta.json` on downgrade is harmless; old code ignores unknown fields.
