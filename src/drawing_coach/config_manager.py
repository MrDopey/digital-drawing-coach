from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv, set_key, unset_key

from drawing_coach.llm_config import LLMConfig
from drawing_coach.paths import config_path as _default_config_path

_log = logging.getLogger("drawing_coach.config_manager")

_NOT_LOADED = object()


class ConfigManager:
    def __init__(
        self,
        config_path: Path | None = None,
        dotenv_path: Path | None = None,
    ) -> None:
        self._config_path = config_path
        self._dotenv_path = dotenv_path
        self._config: LLMConfig | object = _NOT_LOADED

    @property
    def config(self) -> LLMConfig:
        if self._config is _NOT_LOADED:
            raise RuntimeError(
                "ConfigManager.load() must be called before accessing .config"
            )
        return self._config  # type: ignore[return-value]

    def _paths(self) -> tuple[Path, Path]:
        cp = self._config_path or _default_config_path()
        return cp, self._dotenv_path or (cp.parent / ".env")

    def load(self) -> LLMConfig:
        cp, dp = self._paths()
        load_dotenv(dotenv_path=dp, override=False)

        if not cp.exists():
            cfg = LLMConfig()
            _log.info("No config file found, using defaults")
        else:
            try:
                data = json.loads(cp.read_text())
                known = set(LLMConfig.__dataclass_fields__)
                cfg = LLMConfig(**{k: v for k, v in data.items() if k in known})
                _log.info("Config loaded from %s", cp)
            except Exception:
                cfg = LLMConfig()
                _log.info("Config file invalid, using defaults")

        # Apply env var overrides (real shell env vars take precedence via override=False above)
        if m := os.environ.get("DRAWING_COACH_MODEL", ""):
            cfg.model = m
        if b := os.environ.get("DRAWING_COACH_API_BASE", ""):
            cfg.api_base = b
        cfg.api_key = os.environ.get("DRAWING_COACH_API_KEY", "")

        if cfg.api_key:
            _log.info("API key present")
        else:
            _log.warning(
                "No API key configured — LLM calls will fail unless using a local model"
            )

        self._config = cfg
        return cfg

    def save(self, config: LLMConfig) -> None:
        cp, dp = self._paths()
        cp.parent.mkdir(parents=True, exist_ok=True)

        data = {k: v for k, v in asdict(config).items() if k != "api_key"}
        cp.write_text(json.dumps(data, indent=2))

        try:
            if config.api_key:
                set_key(str(dp), "DRAWING_COACH_API_KEY", config.api_key)
                os.environ["DRAWING_COACH_API_KEY"] = config.api_key
            else:
                unset_key(str(dp), "DRAWING_COACH_API_KEY")
                os.environ.pop("DRAWING_COACH_API_KEY", None)
        except PermissionError as e:
            raise PermissionError(f"Could not save API key: {e}") from e

        self._config = config

    def export_portable(self, path: str | Path) -> None:
        data = {k: v for k, v in asdict(self.config).items() if k != "api_key"}
        Path(path).write_text(json.dumps(data, indent=2))

    def import_portable(self, path: str | Path) -> LLMConfig:
        data = json.loads(Path(path).read_text())
        known = set(LLMConfig.__dataclass_fields__)
        return LLMConfig(**{k: v for k, v in data.items() if k in known})
