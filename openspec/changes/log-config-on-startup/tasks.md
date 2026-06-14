## 1. Implementation

- [ ] 1.1 Add `_SECRET_FIELDS = re.compile(r'key|token|secret|password', re.IGNORECASE)` constant to `config_manager.py`
- [ ] 1.2 Add `_redact(field_name: str, value: str) -> str` helper: returns `value[:5] + "…"` if secret and len ≥ 5, `"(not set)"` if secret and len < 5, else `str(value)`
- [ ] 1.3 Add `log_config(config: LLMConfig) -> None` method to `ConfigManager`: iterates `dataclasses.asdict(config).items()`, calls `_redact`, logs each at DEBUG via `_log.debug("config: %s = %s", k, v)`
- [ ] 1.4 Call `self.log_config(cfg)` at the end of `ConfigManager.load()` before returning

## 2. Tests

- [ ] 2.1 Unit test `_redact`: non-secret field returned as-is; secret field with long value shows 5-char prefix + `…`; secret field empty or short shows `(not set)`
- [ ] 2.2 Unit test `log_config`: all fields logged at DEBUG; `api_key` is redacted; non-secret fields are not redacted (use `caplog` fixture)

## 3. Documentation

- [ ] 3.1 Update `README.md` to note that DEBUG logging shows active config on startup (with secret redaction)
- [ ] 3.2 Review `.claude/CLAUDE.md` — no new UI conventions; no changes needed
- [ ] 3.3 Review `openspec/config.yaml` — no recurring gap identified; no changes needed
- [ ] 3.4 Run `uv run pytest` and confirm all tests pass
