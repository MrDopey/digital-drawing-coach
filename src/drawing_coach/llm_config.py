from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

import keyring

_SERVICE = "drawing-coach"
_CONFIG_PATH = Path.home() / ".drawing-coach" / "config.json"
_SESSIONS_DIR = Path.home() / ".drawing-coach" / "sessions"


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
        try:
            return keyring.get_password(_SERVICE, "api_key") or ""
        except keyring.errors.NoKeyringError:
            return ""

    @api_key.setter
    def api_key(self, value: str) -> None:
        if value:
            keyring.set_password(_SERVICE, "api_key", value)
        else:
            try:
                keyring.delete_password(_SERVICE, "api_key")
            except keyring.errors.PasswordDeleteError:
                pass

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
            return f"The user is currently practising: **{s}**. Tailor all feedback to conventions and techniques specific to that style."
        return f"The user is currently focusing on: **{s}**."

    def save(self) -> None:
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        _CONFIG_PATH.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls) -> "LLMConfig":
        if not _CONFIG_PATH.exists():
            cfg = cls()
        else:
            try:
                data = json.loads(_CONFIG_PATH.read_text())
                known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
                cfg = cls(**{k: v for k, v in data.items() if k in known})
            except Exception:
                cfg = cls()
        # Environment variable overrides (used in headless / Docker mode)
        if os.environ.get("DRAWING_COACH_MODEL"):
            cfg.model = os.environ["DRAWING_COACH_MODEL"]
        if os.environ.get("DRAWING_COACH_API_BASE"):
            cfg.api_base = os.environ["DRAWING_COACH_API_BASE"]
        return cfg

    def export_portable(self, path: str | Path) -> None:
        data = asdict(self)
        Path(path).write_text(json.dumps(data, indent=2))

    @classmethod
    def import_portable(cls, path: str | Path) -> "LLMConfig":
        data = json.loads(Path(path).read_text())
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})
