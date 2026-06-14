## Context

`FeedbackEngine._build_system_prompt` currently assembles the system prompt from a fixed base prompt, an optional style fragment, optional custom instructions, and a mode template. There is no injection point for cross-session context. Sessions are identified by their directory name (`YYYY-MM-DD_HHMMSS`); `sessions_dir()` is the data root. No `memory.json` file exists today.

## Goals / Non-Goals

**Goals:**
- `memory.json` persists across sessions in the app data directory
- Observations extracted from (or alongside) each LLM feedback response
- Coach's notes injected into every subsequent system prompt
- Memory viewer and progress panel accessible from the main window

**Non-Goals:**
- Automatic observation extraction via a separate LLM call on every feedback (too slow/expensive for v1; structured extraction is deferred)
- Per-category observation limits (flat cap of 200 total)
- Syncing memory across devices

## Decisions

### 1. Observation extraction: parse structured JSON block from LLM response (v1)

The LLM is asked (via a mode-agnostic system prompt addition) to append a `<!-- observations: [...] -->` HTML comment to its response containing a JSON array of `{category, note}` objects. `MemoryStore.extract_observations(response_text)` parses this comment and strips it before display. If absent or malformed, no observations are recorded for that response.

**Alternative considered:** second LLM call to extract observations — rejected for v1 (doubles cost and latency). Can be upgraded later.

### 2. `memory.json` lives at `data_dir / "memory.json"` (sibling to `sessions/`)

`paths.memory_path()` returns `sessions_dir().parent / "memory.json"`. This keeps it in the same XDG data directory as sessions and is easy to back up.

### 3. `MemoryStore` is a thin wrapper: load-on-init, mutate in memory, save-on-change

`MemoryStore` loads on first access and exposes `append(obs)`, `delete(idx)`, `clear()`, `save()`, and `summarise(max_observations=20) -> str`. `summarise` returns a brief "coach's notes" Markdown block for prompt injection (most-recent N observations, sorted by category recurrence). Saving is synchronous on mutation — file is small (< 50 KB at 200 entries).

### 4. Prompt injection: `FeedbackEngine._build_system_prompt` accepts `coach_notes: str = ""`

`MainWindow` (or the feedback trigger path) calls `memory_store.summarise()` and passes it to `request_feedback(..., coach_notes=...)`. `_build_system_prompt` prepends it between the base prompt and the style fragment. Session count is passed as part of the notes block (e.g. "You have worked with this student across N sessions.").

**Alternative:** `MemoryStore` is injected into `FeedbackEngine` constructor — tighter coupling; the parameter approach keeps the engine testable without a store.

### 5. Memory viewer: `MemoryViewerDialog` sorted by category then reverse date

`QTreeWidget` with top-level items per category, child items per observation (`date — note`). Delete button removes the selected observation. Clear All triggers `QMessageBox` confirmation. Export calls `QFileDialog.getSaveFileName` and copies `memory.json`. Read-only summary text area at the top shows the current coach's notes block.

### 6. Progress panel: `ProgressPanel(QWidget)` added as a tab in Settings or as a standalone dialog

Lists categories with observation counts and session counts (e.g. "Perspective: 7 observations across 4 sessions"). Below: session date timeline as a simple `QListWidget` of session start dates loaded from `sessions_dir()` meta files.

## Risks / Trade-offs

- [LLM may not always emit the `<!-- observations -->` comment] → silently ignored; memory degrades gracefully to empty rather than erroring
- [Observation quality depends on LLM compliance] → acceptable for v1; structured extraction via second call can replace this later
- [200-entry cap may feel arbitrary to power users] → cap is configurable via `config.json` in a future iteration; hardcoded for v1
