## 1. Data layer — MemoryStore

- [ ] 1.1 Add `memory_path() -> Path` to `paths.py` (returns `sessions_dir().parent / "memory.json"`)
- [ ] 1.2 Create `src/drawing_coach/memory_store.py` with `@dataclass Observation(date, session_id, category, note)` and `MemoryStore`
- [ ] 1.3 `MemoryStore.__init__`: load `memory.json` on init (empty list if file absent or malformed)
- [ ] 1.4 `MemoryStore.append(obs)`: add observation, prune oldest if total > 200, save
- [ ] 1.5 `MemoryStore.delete(idx)`: remove observation by index, save
- [ ] 1.6 `MemoryStore.clear()`: empty the list, save
- [ ] 1.7 `MemoryStore.summarise(max_obs=20) -> str`: return Markdown coach's notes block (session count + most recent N observations); return `""` if empty
- [ ] 1.8 `MemoryStore.extract_and_append(response_text, session_id) -> str`: parse `<!-- observations: [...] -->` comment, append valid observations, return response text with comment stripped

## 2. Prompt injection

- [ ] 2.1 Add `coach_notes: str = ""` parameter to `FeedbackEngine._build_system_prompt`; prepend to assembled prompt when non-empty
- [ ] 2.2 Add observation-extraction instruction to the base `_SYSTEM_PROMPT` (ask LLM to append `<!-- observations: [...] -->`)
- [ ] 2.3 In the feedback trigger path (MainWindow or FeedbackPanel), call `memory_store.summarise()` and pass to `request_feedback`
- [ ] 2.4 After each successful `FeedbackResponse`, call `memory_store.extract_and_append(response.text, session_id)` and update `response.text` with the stripped text

## 3. Memory viewer dialog

- [ ] 3.1 Create `src/drawing_coach/memory_viewer.py` with `MemoryViewerDialog(QDialog)`
- [ ] 3.2 Top read-only `QTextEdit` showing current `memory_store.summarise()` output (coach's notes preview)
- [ ] 3.3 `QTreeWidget` body: top-level items per category (sorted by recurrence desc), child items `date — note` with per-row Delete button
- [ ] 3.4 Toolbar buttons: Clear All (with `QMessageBox` confirmation), Export (`QFileDialog.getSaveFileName` → copy `memory.json`)
- [ ] 3.5 Add Memory Viewer action to main window menu (Settings or Tools menu)

## 4. Progress panel

- [ ] 4.1 Create `src/drawing_coach/progress_panel.py` with `ProgressPanel(QWidget)` or `ProgressDialog(QDialog)`
- [ ] 4.2 Theme summary: `QListWidget` listing categories with "N observations across M sessions" labels (sorted by observation count desc)
- [ ] 4.3 Session timeline: `QListWidget` listing session start dates from `sessions_dir()` meta.json files (reverse-chron)
- [ ] 4.4 Add Progress action to main window menu

## 5. Tests

- [ ] 5.1 Unit tests for `MemoryStore.append` (normal, cap overflow, save round-trip)
- [ ] 5.2 Unit tests for `MemoryStore.extract_and_append` (valid comment, absent comment, malformed comment)
- [ ] 5.3 Unit test for `MemoryStore.summarise` (empty, non-empty, >20 observations)
- [ ] 5.4 Unit test for `FeedbackEngine._build_system_prompt` with and without `coach_notes`

## 6. Documentation

- [ ] 6.1 Update `README.md` with long-term memory feature description (memory.json location, what it stores, how to view/clear)
- [ ] 6.2 Update `.claude/CLAUDE.md` memory index: note that `memory.json` stores cross-session drawing observations and is separate from the Claude Code memory system
- [ ] 6.3 Review `openspec/config.yaml` — no recurring gap identified; no changes needed
- [ ] 6.4 Run `uv run pytest` and confirm all tests pass
