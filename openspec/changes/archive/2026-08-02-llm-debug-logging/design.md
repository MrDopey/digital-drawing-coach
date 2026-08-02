## Context

As of the `structured-json-output-fallback` change (merged to `main`), `FeedbackEngine.request_feedback()` no longer makes a single `litellm.completion()` call — it tries `_call_structured()` first (uses `response_format` to request strict JSON matching `_STRUCTURED_RESPONSE_SCHEMA`), and only if that raises (and structured output isn't already disabled for the process, via the `_structured_output_disabled` module flag) falls back to `_call_prose()` (the original free-text + regex-extracted-JSON path). Both methods build their own `kwargs` via a shared `self._base_kwargs()` helper and call `litellm.completion(**kwargs)` independently, so a single feedback request can now produce **one or two** LLM calls. Distinguishing which path actually produced a given response is itself diagnostically important — a bad overlay annotation behaves very differently depending on whether it came from the schema-constrained structured path or the regex-parsed prose fallback.

The other three call sites are unaffected by that change: `diagnostics.check_llm()` (`diagnostics.py:142`, text-only "hi" probe), `SettingsDialog._test_connection()` (`settings_dialog.py:267`, text-only "hi" probe), and `MemoryStore._try_resummarize()` (`memory_store.py:240`, text-only re-summarisation prompt) each still make exactly one `litellm.completion()` call. None of the app's LLM calls persist their request or response today.

LiteLLM (already a dependency, confirmed installed at v1.85.0) ships a first-class instrumentation hook for exactly this purpose: `litellm.integrations.custom_logger.CustomLogger`, a base class with `log_success_event(kwargs, response_obj, start_time, end_time)` and `log_failure_event(kwargs, response_obj, start_time, end_time)` methods to override. Registering an instance via `litellm.callbacks = [...]` makes LiteLLM invoke it automatically after **every** `litellm.completion()` call in the process — verified directly against the installed version:

- `kwargs["messages"]` is the exact, unmodified messages list passed to `completion()`, including full base64 `image_url` data URIs when present.
- A `metadata={"debug_label": "..."}` kwarg passed into `completion()` round-trips unchanged to `kwargs["litellm_params"]["metadata"]["debug_label"]` inside the callback — LiteLLM's supported mechanism for passing caller-supplied context through to logging.
- On success, `response_obj` is a `litellm.types.utils.ModelResponse` — the same type `feedback_engine.py` already reads via `.choices[0].message.content`.
- On failure, `kwargs["exception"]` holds the raised exception, regardless of its specific type (`AuthenticationError`, `RateLimitError`, `APIConnectionError`, etc.) — `log_failure_event` fires uniformly for all of them.
- The callback runs on a background `ThreadPoolExecutor` thread, after the call already returned/raised to the caller — it cannot block or delay any call site.

This means debug capture does **not** require touching each call site's control flow, exception handling, or return values at all. Each site only needs to attach a `debug_label` via the `metadata` kwarg it already builds (`kwargs: dict[str, Any] = {...}`) so the callback can name its output — the callback itself is registered exactly once, and its logic never needs to be duplicated or kept in sync across four call sites.

`LLMConfig` (`llm_config.py`) is a flat dataclass, generically persisted via `ConfigManager`'s `asdict()`/field-introspection (`config_manager.py:53-96`) — a new field needs no config-manager changes. All four call sites already share one live `LLMConfig` instance passed around at app wiring time, and `SettingsDialog._save()` mutates that same instance's fields in place (e.g. `self._config.lookback_frames = ...`) rather than replacing it — so a callback holding a reference to that instance sees setting changes immediately, with no re-registration needed. `paths.py` centralizes on-disk locations (`config_path()`, `sessions_dir()`, `memory_path()`).

## Goals / Non-Goals

**Goals:**
- Let a user opt in, via one Settings checkbox, to persisting the request and response of every LLM call the app makes — not just feedback requests, and not just the four call sites known today.
- Use LiteLLM's own logging hook rather than hand-rolled instrumentation, so there's exactly one implementation of the capture logic and no per-call-site duplication to keep in sync.
- Keep the feature fully inert (no behavior change, no disk writes, no callback overhead beyond a config-flag check) when disabled, which is the default.
- The capture must be a pure side effect: no call site's return value, exception type, or control flow changes because of it.

**Non-Goals:**
- No UI to browse, list, or delete captured debug logs — files just land in a documented directory.
- No automatic pruning/rotation (unlike `app-logging`'s size-capped rotation) — this is a manually-enabled diagnostic tool; the user is expected to enable it briefly and clean up manually. README documents this explicitly.
- No redaction/anonymization of captured screenshots or prompt text.
- No change to `overlay_renderer.py`, the annotation JSON schema, or any existing spec's requirements.
- Not building on OpenTelemetry: OTel targets cross-service trace correlation shipped to an external backend, and its span-attribute model is a poor fit for embedding full-resolution PNGs. LiteLLM's callback hook is purpose-built for exactly this LLM-input/output capture use case and needs no new dependency.

## Decisions

**New config field:** `LLMConfig.debug_log_llm_io: bool = False`. Persists/loads automatically via the existing generic mechanism.

**Settings UI placement:** a `QCheckBox` added to the existing "LLM" tab in `settings_dialog.py`, below "Custom Instructions", with a tooltip warning it persists LLM requests/responses (including drawing screenshots) to disk.

**`CustomLogger` subclass, registered once:** new module `src/drawing_coach/llm_debug_log.py`:

```python
class DebugIOLogger(litellm.integrations.custom_logger.CustomLogger):
    def __init__(self, config: LLMConfig) -> None:
        self._config = config

    def log_success_event(self, kwargs, response_obj, start_time, end_time) -> None:
        if not self._config.debug_log_llm_io:
            return
        self._write(kwargs, response_obj.choices[0].message.content)

    def log_failure_event(self, kwargs, response_obj, start_time, end_time) -> None:
        if not self._config.debug_log_llm_io:
            return
        self._write(kwargs, kwargs.get("exception"))

    def _write(self, kwargs, result) -> None:
        try:
            ...  # extract images/text from kwargs["messages"], write result, see below
        except Exception:
            _log.warning("Debug log write failed", exc_info=True)
```

- `_write` walks `kwargs["messages"]`: each `content` part with `type == "image_url"` is decoded from its base64 payload and written as `frame_NN.png`; every text part (system and user, role-prefixed) is concatenated into `request.txt`.
- `result` is written to `response.txt` if it's a string, or to `error.txt` (`type(result).__name__` + message) if it's an `Exception`.
- Directory: `paths.debug_log_dir() / f"<ISO8601-timestamp>_<label>"`, where `label = kwargs.get("litellm_params", {}).get("metadata", {}).get("debug_label", "unknown")`.
- The whole `_write` body is wrapped in `try/except Exception`, logged at WARNING, never raised — since this already runs on LiteLLM's background callback thread, an uncaught exception here would only be swallowed by LiteLLM anyway, but catching explicitly keeps the WARNING log under this module's control.

**Registration:** one instance is constructed with the app's shared `LLMConfig` and appended to `litellm.callbacks` once during app startup (wherever the app already does one-time setup before any feedback/diagnostics/settings code can run — e.g. alongside `ConfigManager.load()`). No dynamic add/remove on setting toggle is needed: the instance holds a live reference to `config` and checks `debug_log_llm_io` on every event, so flipping the checkbox and saving takes effect on the next call with no restart.

**Call-site changes — minimal, uniform, and additive:** each site adds exactly one entry to the `kwargs` dict it already builds before calling `litellm.completion(**kwargs)`:
```python
kwargs["metadata"] = {"debug_label": "diagnostics_check_llm"}    # or "settings_test_connection",
                                                                   # "memory_resummarize"
```
`feedback_engine.py`'s `_base_kwargs()` gains a `label: str` parameter so both call paths can pass their own:
```python
def _base_kwargs(self, label: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"model": self._config.model, "metadata": {"debug_label": label}}
    ...
```
- `_call_structured()` calls `self._base_kwargs(f"feedback_{mode}_structured")`.
- `_call_prose()` calls `self._base_kwargs(f"feedback_{mode}_prose")`.

This makes it visible in the debug log directory names which path actually produced each response — e.g. `..._feedback_overlay_structured` succeeding vs. a `..._feedback_overlay_structured` failure (`error.txt`) immediately followed by a `..._feedback_overlay_prose` success, showing structured output failed and prose fallback took over for that request.

No `try/except` restructuring, no explicit logging call, no branching on success/failure — LiteLLM's callback dispatch handles both outcomes uniformly via the registered `DebugIOLogger`.

**On-disk layout:** `paths.debug_log_dir() -> Path` returns `sessions_dir().parent / "debug_logs"`, consistent with `memory_path()`'s sibling-of-`sessions_dir` pattern. Each call gets its own subdirectory (`frame_00.png`, ..., `request.txt`, and `response.txt` or `error.txt`).

## Risks / Trade-offs

- **Disk usage growth:** every enabled call writes at least a text file, and feedback calls write full-resolution PNGs. Mitigated by defaulting off, documenting the directory in the README, and not auto-pruning.
- **Privacy:** persisted PNGs are raw drawing-session screenshots; persisted text includes full prompts (custom instructions, coach's notes). Mitigated by requiring explicit opt-in with a tooltip warning, off by default.
- **Asynchronous write timing:** the callback fires on a LiteLLM-managed background thread after the call returns, so debug artifacts for the very last call before app exit could theoretically not finish writing before the process closes. Acceptable for a manually-enabled diagnostic feature; not worth adding shutdown synchronization for.
- **Coupling to LiteLLM's callback API:** this relies on `litellm.integrations.custom_logger.CustomLogger` and the `metadata` passthrough behavior remaining stable across LiteLLM versions. Both are long-standing, documented parts of LiteLLM's public logging integration surface (used the same way by its Langfuse/Helicone/etc. integrations), so this is a reasonable dependency, not a private/internal detail.
