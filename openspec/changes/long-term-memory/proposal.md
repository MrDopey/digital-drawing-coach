## Why

The coach gives the same generic advice every session because it has no memory of past observations — it cannot say "you've struggled with perspective across four sessions" or adjust its tone for a returning student vs. a first-time user. Feedback quality improves substantially when the LLM has structured context about the user's recurring patterns.

## What Changes

- A `memory.json` file is maintained in the app data directory across sessions, storing a list of observations (each with `date`, `session_id`, `category`, `note`)
- After each feedback response the LLM (or a post-processing step) appends new observations; total observations are capped at 200 (oldest pruned on overflow)
- Before each LLM request, recent observations are summarised into a short "coach's notes" block prepended to the system prompt; the prompt also includes the total session count so the LLM can calibrate tone
- Settings / dedicated panel exposes a read-only memory summary view
- **Memory viewer**: reverse-chronological list grouped by category; per-row delete; clear-all with confirmation dialog; export `memory.json` to user-chosen location
- **Progress panel / tab**: summarises recurring themes (e.g. "Perspective mentioned 7 times across 4 sessions") and shows a simple timeline of session dates

## Capabilities

### New Capabilities
- `memory-store`: Persist observations to `memory.json`; append, cap, prune, and load
- `memory-prompt-injection`: Summarise observations into a "coach's notes" block and inject into the LLM system prompt before each request
- `memory-viewer`: UI to view, delete, clear, and export stored observations
- `progress-panel`: UI tab/panel summarising recurring themes and session frequency timeline

### Modified Capabilities
- `llm-feedback`: `FeedbackEngine._build_system_prompt` must accept and prepend an optional coach's notes block supplied by the memory layer

## Impact

- New `src/drawing_coach/memory_store.py` — `MemoryStore`: load, append, prune, save, summarise
- New `src/drawing_coach/memory_viewer.py` — `MemoryViewerDialog`: grouped list, delete, clear, export
- New `src/drawing_coach/progress_panel.py` — `ProgressPanel`: theme counts + session timeline
- `src/drawing_coach/feedback_engine.py` — `_build_system_prompt` accepts optional `coach_notes: str`
- `src/drawing_coach/paths.py` — new `memory_path() -> Path` helper
- `src/drawing_coach/main_window.py` — wire memory store into feedback flow; add Memory/Progress menu entries
- No new third-party dependencies (json, collections.Counter, datetime all stdlib)
