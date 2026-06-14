from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LLMConfig:
    model: str = ""
    api_base: str = ""
    api_key: str = ""
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

    def is_configured(self) -> bool:
        return bool(self.model)

    def effective_style_label(self) -> str:
        return self.style_focus.strip() or "General"

    def style_prompt_fragment(self) -> str:
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
