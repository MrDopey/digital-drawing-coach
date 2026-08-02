## 1. Config plumbing

- [x] 1.1 Add `debug_log_llm_io: bool = False` to `LLMConfig` in `llm_config.py`
- [x] 1.2 Add `debug_log_dir() -> Path` to `paths.py`, returning `sessions_dir().parent / "debug_logs"`

## 2. Settings UI

- [x] 2.1 Add a `QCheckBox` "Debug logging of LLM input/output" to `SettingsDialog._build_llm_tab()` in `settings_dialog.py`, initialized from `self._config.debug_log_llm_io`, with a tooltip warning that this persists LLM requests/responses (including drawing screenshots) to disk
- [x] 2.2 Wire the checkbox's value back into `self._config.debug_log_llm_io` in the dialog's save handler

## 3. CustomLogger callback

- [x] 3.1 Create `src/drawing_coach/llm_debug_log.py` with `DebugIOLogger(litellm.integrations.custom_logger.CustomLogger)`, holding a reference to the shared `LLMConfig`
- [x] 3.2 Implement `log_success_event`/`log_failure_event`: no-op unless `config.debug_log_llm_io` is `True`, otherwise delegate to a shared `_write(kwargs, result)` (`result` = response text on success, the exception on failure)
- [x] 3.3 Implement `_write`: extract `debug_label` from `kwargs["litellm_params"]["metadata"]["debug_label"]`; walk `kwargs["messages"]` extracting `image_url` parts to `frame_NN.png` and text parts (role-prefixed) into `request.txt`; write `result` to `response.txt` (string) or `error.txt` (`Exception`); target directory `paths.debug_log_dir() / f"<ISO8601-timestamp>_<label>"`
- [x] 3.4 Wrap `_write`'s body in `try/except Exception`, logging a WARNING via a module logger, never raising
- [x] 3.5 Register one `DebugIOLogger(config)` instance into `litellm.callbacks` once at app startup, using the app's shared `LLMConfig` instance

## 4. Attach debug labels at each call site

- [x] 4.1 `feedback_engine.py`: add a `label: str` parameter to `_base_kwargs()`, setting `kwargs["metadata"] = {"debug_label": label}`
- [x] 4.2 `feedback_engine.py`: `_call_structured()` calls `self._base_kwargs(f"feedback_{mode}_structured")`
- [x] 4.3 `feedback_engine.py`: `_call_prose()` calls `self._base_kwargs(f"feedback_{mode}_prose")`
- [x] 4.4 `diagnostics.py check_llm()`: add `kwargs["metadata"] = {"debug_label": "diagnostics_check_llm"}`
- [x] 4.5 `settings_dialog.py _test_connection()`: add `kwargs["metadata"] = {"debug_label": "settings_test_connection"}`
- [x] 4.6 `memory_store.py _try_resummarize()`: add `kwargs["metadata"] = {"debug_label": "memory_resummarize"}`

## 5. Tests

- [x] 5.1 Add `test_llm_debug_log.py`: construct a `DebugIOLogger` directly and call `log_success_event`/`log_failure_event` with representative `kwargs`/`response_obj` fixtures (mirroring the real LiteLLM shapes confirmed during design) — assert: disabled config writes no files; enabled writes `frame_NN.png` per image + `request.txt` + `response.txt` on success; enabled writes `request.txt` + `error.txt` on failure; a write failure (e.g. `debug_log_dir()` uncreatable) logs a WARNING and raises nothing
- [x] 5.2 Add a test confirming `_call_structured()` and `_call_prose()` each build `kwargs` with the expected `metadata.debug_label` (e.g. `feedback_overlay_structured`, `feedback_overlay_prose`) for each mode
- [x] 5.3 Add a test simulating a structured-output failure followed by prose fallback for the same request, asserting two distinct debug-labeled calls occur (one `_structured`, one `_prose`)
- [x] 5.4 Add equivalent `metadata.debug_label` assertions for `diagnostics.check_llm()`, `SettingsDialog._test_connection()`, and `MemoryStore._try_resummarize()`

## 6. Documentation

- [x] 6.1 Document the debug log directory location, per-call subdirectory naming, and that it covers every LLM call site — including both the structured and prose-fallback feedback paths — via a LiteLLM logging callback, in `README.md`
- [x] 6.2 Note in `README.md` that the setting is off by default, persists raw prompts/screenshots, and is not auto-pruned
