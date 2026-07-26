## 1. Data layer — MemoryStore

- [x] 1.1 Add `memory_path() -> Path` (returns `sessions_dir().parent / "memory.json"`) and `memory_summaries_path() -> Path` (returns `sessions_dir().parent / "memory_summaries.json"`) to `paths.py`
- [x] 1.2 Create `src/drawing_coach/memory_store.py` with `@dataclass Observation(date, session_id, category, note)`, `@dataclass Summary(date, text, observation_count)`, and `MemoryStore`
- [x] 1.3 `MemoryStore.__init__`: load `memory.json` (`observations` list) and `memory_summaries.json` (`summaries` list + `last_resummarized_count` counter) independently — each defaults to empty/0 if its file is absent or malformed; missing one file doesn't block loading the other
- [x] 1.4 `MemoryStore.append(obs)`: add observation, prune oldest if total > `LLMConfig.memory_max_observations`, save `memory.json` only
- [x] 1.5 `MemoryStore.delete(idx)`: remove observation by index, save `memory.json` only
- [x] 1.6 `MemoryStore.clear()`: empty both the `observations` list and the `summaries` list, reset `last_resummarized_count` to 0, save both files
- [x] 1.7 `MemoryStore.summarise(max_obs=20) -> str`: return Markdown coach's notes block (session count + most recent N observations, formatted raw); return `""` if empty
- [x] 1.8 `MemoryStore.extract_and_append(response_text, session_id) -> str`: parse `<!-- observations: [...] -->` comment, append valid observations, return response text with comment stripped
- [x] 1.9 Add `memory_resummarize_interval: int = 20` to `LLMConfig` (default re-summarises every 20 appended observations; `0` opts out and keeps notes raw forever)
- [x] 1.9a Add `memory_max_observations: int = 200` to `LLMConfig`; replaces the hardcoded 200 cap so power users can raise or lower it
- [x] 1.9b Add `memory_summary_history_max: int = 200` to `LLMConfig`; caps the `summaries` list independently of `memory_max_observations`
- [x] 1.10 `MemoryStore`: track count of observations appended since last re-summarisation (persisted as `last_resummarized_count` in `memory_summaries.json`, alongside the `summaries` list)
- [x] 1.11 `MemoryStore.summarise()`: when `memory_resummarize_interval > 0` and the threshold is reached, call the LLM once to condense raw notes since the last summary (plus the prior summary's text, if any) into a shorter block, **append** it as a new `Summary` entry to `summaries`, prune oldest if total exceeds `memory_summary_history_max`, reset the counter, and save `memory_summaries.json` only; on failure, log a debug entry and fall back to the previous raw/summary notes unchanged
- [x] 1.12 `MemoryStore.summarise()`: build the returned coach's-notes block from the *most recent* entry in `summaries` (if any) plus raw observations appended since that entry's `date` — never concatenate multiple summary entries

## 2. Coach's notes context

- [x] 2.1 Add `coach_notes: str = ""` parameter to `FeedbackEngine._build_system_prompt`; **append** it after the mode template (not prepended before the persona) so the persona/style/custom-instructions/mode-template prefix stays stable for prompt caching
- [x] 2.2 Add observation-extraction instruction to the base `_SYSTEM_PROMPT` (ask LLM to append `<!-- observations: [...] -->`)
- [x] 2.3 In the feedback trigger path (MainWindow or FeedbackPanel), call `memory_store.summarise()` and pass to `request_feedback`
- [x] 2.4 After each successful `FeedbackResponse`, call `memory_store.extract_and_append(response.text, session_id)` and update `response.text` with the stripped text
- [x] 2.5 Add a "Memory" tab to `SettingsDialog` (`settings_dialog.py`, alongside the existing LLM/Capture/Stuck Detection/History tabs) with three `QSpinBox` controls — `memory_resummarize_interval` (default 20, minimum 0, tooltip explaining `0` keeps coach's notes raw and disables periodic re-summarisation), `memory_max_observations` (default 200, minimum 1, tooltip explaining this is the total observation cap before oldest entries are pruned), and `memory_summary_history_max` (default 200, minimum 1, tooltip explaining this caps the retained summary history, independent of the observation cap) — all wired into `_save`/`_apply` and the config import/export round-trip like the existing fields

## 3. Memory viewer dialog

- [x] 3.1 Create `src/drawing_coach/memory_viewer.py` with `MemoryViewerDialog(QDialog)`
- [x] 3.2 Top read-only `QTextEdit` showing current `memory_store.summarise()` output (coach's notes preview)
- [x] 3.3 `QTreeWidget` body: top-level items per category (sorted by recurrence desc), child items `date — note` with per-row Delete button
- [x] 3.4 Toolbar buttons: Clear All (with `QMessageBox` confirmation, calls `memory_store.clear()` — resets both files), Export (`QFileDialog.getExistingDirectory` → copy `memory.json` and, if present, `memory_summaries.json` into the chosen folder)
- [x] 3.5 Add Memory Viewer action to main window menu (Settings or Tools menu)

## 4. Progress panel

- [x] 4.1 Create `src/drawing_coach/progress_panel.py` with `ProgressPanel(QWidget)` or `ProgressDialog(QDialog)`
- [x] 4.2 Theme summary: `QListWidget` listing categories with "N observations across M sessions" labels (sorted by observation count desc)
- [x] 4.3 Session timeline: `QListWidget` listing session start dates from `sessions_dir()` meta.json files (reverse-chron)
- [x] 4.4 Add Progress action to main window menu

## 5. Tests

- [x] 5.1 Unit tests for `MemoryStore.append` (normal, cap overflow at the configured `memory_max_observations`, custom non-default cap, save round-trip)
- [x] 5.2 Unit tests for `MemoryStore.extract_and_append` (valid comment, absent comment, malformed comment)
- [x] 5.3 Unit test for `MemoryStore.summarise` (empty, non-empty, >20 observations)
- [x] 5.4 Unit test for `FeedbackEngine._build_system_prompt` with and without `coach_notes` — assert `coach_notes` is appended after the mode template and the prefix (persona/style/custom-instructions/mode-template) is unchanged when `coach_notes` varies
- [x] 5.5 Unit tests for `MemoryStore.summarise` re-summarisation: default (`memory_resummarize_interval=20`) triggers condensation once the threshold is reached; `memory_resummarize_interval=0` never triggers an LLM call; threshold reached triggers exactly one condensation call and resets the counter; condensation failure falls back to prior notes unchanged
- [x] 5.6 Unit tests for the `summaries` history: condensation appends a new `Summary` rather than overwriting the previous one; cap overflow at `memory_summary_history_max` prunes the oldest summaries; `summarise()`'s output is built from only the most recent summary plus post-summary raw observations, not a concatenation of multiple summaries
- [x] 5.7 Unit tests for the two-file split: `memory.json` and `memory_summaries.json` load/save independently (one missing/malformed doesn't block the other); appending an observation only rewrites `memory.json`; appending a summary only rewrites `memory_summaries.json`; `clear()` resets both files and the resummarisation counter

## 6. Documentation

- [x] 6.1 Update `README.md` with long-term memory feature description (`memory.json` and `memory_summaries.json` locations, what each stores, how to view/clear)
- [x] 6.2 Update `.claude/CLAUDE.md` memory index: note that `memory.json` (raw observations) and `memory_summaries.json` (re-summarisation history) store cross-session drawing observations and are separate from the Claude Code memory system
- [x] 6.3 Review `openspec/config.yaml` — no recurring gap identified; no changes needed
- [x] 6.4 Run `uv run pytest` and confirm all tests pass
