from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv, set_key, unset_key

from drawing_coach import env
from drawing_coach.paths import config_path, sessions_dir

load_dotenv(dotenv_path=config_path().parent / ".env", override=False)

_log = logging.getLogger("drawing_coach.llm_config")


@dataclass
class LLMConfig:
    model: str = ""
    api_base: str = ""
    custom_instructions: str = ""
    capture_interval: int = 30
    hotkey: str = "<ctrl>+<shift>+f"
    # Stuck detection
    stuck_threshold: float = 10.0
    stuck_consecutive: int = 3
    stuck_cooldown_minutes: int = 5
    # History / capture
    lookback_frames: int = 2
    dedup_threshold: float = 2.0
    history_retention_sessions: int = 10
    # Style / focus
    style_focus: str = ""
    style_focus_is_preset: bool = True

    @property
    def api_key(self) -> str:
        return env.api_key()

    @api_key.setter
    def api_key(self, value: str) -> None:
        dotenv_path = config_path().parent / ".env"
        try:
            if value:
                set_key(str(dotenv_path), "DRAWING_COACH_API_KEY", value)
            else:
                unset_key(str(dotenv_path), "DRAWING_COACH_API_KEY")
        except PermissionError as e:
            raise PermissionError(f"Could not save API key: {e}") from e

    def is_configured(self) -> bool:
        return bool(self.model)

    def effective_style_label(self) -> str:
        """Returns the display label to show in 'Coaching for: X'."""
        return self.style_focus.strip() or "General"

    def style_prompt_fragment(self) -> str:
        """Returns the system-prompt injection string, or empty string if none set."""
        s = self.style_focus.strip()
        if not s:
            return ""
        if self.style_focus_is_preset:
            return (
                f"The user is currently practising: **{s}**."
                " Tailor all feedback to conventions and techniques"
                " specific to that style."
            )
        return f"The user is currently focusing on: **{s}**."

    def save(self) -> None:
        p = config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        p.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls) -> "LLMConfig":
        p = config_path()
        if not p.exists():
            cfg = cls()
            _log.info("No config file found, using defaults")
        else:
            try:
                data = json.loads(p.read_text())
                known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
                cfg = cls(**{k: v for k, v in data.items() if k in known})
                _log.info("Config loaded from %s", p)
            except Exception:
                cfg = cls()
                _log.info("No config file found, using defaults")
        # Environment variable overrides (used in headless / Docker mode)
        if env.model():
            cfg.model = env.model()
        if env.api_base():
            cfg.api_base = env.api_base()
        if env.api_key():
            _log.info("API key present")
        else:
            _log.warning(
                "No API key configured — LLM calls will fail unless using a local model"
            )
        return cfg

    def export_portable(self, path: str | Path) -> None:
        data = asdict(self)
        Path(path).write_text(json.dumps(data, indent=2))

    @classmethod
    def import_portable(cls, path: str | Path) -> "LLMConfig":
        data = json.loads(Path(path).read_text())
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})
