from __future__ import annotations

import base64
import logging
from datetime import datetime
from typing import Any

from litellm.integrations.custom_logger import CustomLogger

from drawing_coach import paths
from drawing_coach.llm_config import LLMConfig

_log = logging.getLogger("drawing_coach.llm_debug_log")


class DebugIOLogger(CustomLogger):
    """LiteLLM callback that persists request/response of every LLM call to
    disk when `LLMConfig.debug_log_llm_io` is enabled. See design.md for the
    on-disk layout."""

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

    def _write(self, kwargs: dict[str, Any], result: Any) -> None:
        try:
            metadata = kwargs.get("litellm_params", {}).get("metadata") or {}
            label = metadata.get("debug_label", "unknown")
            timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
            out_dir = paths.debug_log_dir() / f"{timestamp}_{label}"
            out_dir.mkdir(parents=True, exist_ok=True)

            text_lines: list[str] = []
            frame_idx = 0
            for message in kwargs.get("messages") or []:
                role = str(message.get("role", "")).upper()
                content = message.get("content")
                if isinstance(content, str):
                    text_lines.append(f"{role}: {content}")
                    continue
                for part in content or []:
                    part_type = part.get("type")
                    if part_type == "text":
                        text_lines.append(f"{role}: {part.get('text', '')}")
                    elif part_type == "image_url":
                        url = part.get("image_url", {}).get("url", "")
                        _, _, b64_data = url.partition(",")
                        if b64_data:
                            frame_path = out_dir / f"frame_{frame_idx:02d}.png"
                            frame_path.write_bytes(base64.b64decode(b64_data))
                            frame_idx += 1

            (out_dir / "request.txt").write_text("\n\n".join(text_lines))

            if isinstance(result, Exception):
                (out_dir / "error.txt").write_text(f"{type(result).__name__}: {result}")
            else:
                (out_dir / "response.txt").write_text(result or "")
        except Exception:
            _log.warning("Debug log write failed", exc_info=True)
