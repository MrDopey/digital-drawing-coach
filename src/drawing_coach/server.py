"""Headless HTTP API server — no GUI, no PyQt6 imports."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from drawing_coach._version import __version__
from drawing_coach.llm_config import LLMConfig
from drawing_coach.window_manager import WindowManager
from drawing_coach.capture_engine import CaptureEngine
from drawing_coach.feedback_engine import FeedbackEngine, FeedbackResponse


# ---- Global state -------------------------------------------------------

_config: LLMConfig | None = None
_capture: CaptureEngine | None = None
_feedback: FeedbackEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _config, _capture, _feedback
    _config = LLMConfig.load()
    _config = _apply_env_overrides(_config)
    _manager = WindowManager()
    _capture = CaptureEngine(_manager, config=_config)
    _capture.start()
    _feedback = FeedbackEngine(_config)
    yield
    if _capture:
        _capture.stop()


app = FastAPI(title="Drawing Coach API", version=__version__, lifespan=lifespan)


# ---- Models -------------------------------------------------------------

class FeedbackRequest(BaseModel):
    mode: str = "full_critique"


class ConfigUpdate(BaseModel):
    model: str | None = None
    api_base: str | None = None
    custom_instructions: str | None = None
    lookback_frames: int | None = None
    style_focus: str | None = None


# ---- Endpoints ----------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "version": __version__}


@app.post("/capture")
def capture():
    if _capture is None:
        raise HTTPException(503, "Server not ready")
    if _capture.target is None:
        raise HTTPException(422, detail="No drawing window configured")
    frame = _capture.capture_once()
    if frame is None:
        raise HTTPException(422, detail="Capture failed — window may be unavailable")
    return {
        "frame_path": str(frame.path) if frame.path else None,
        "timestamp": frame.timestamp.isoformat(),
    }


@app.post("/feedback")
def feedback(req: FeedbackRequest = FeedbackRequest()):
    if _feedback is None or _capture is None:
        raise HTTPException(503, "Server not ready")
    frames = _capture.get_frames()
    if not frames:
        raise HTTPException(422, detail="No frames captured yet")
    result = _feedback.request_feedback(frames, req.mode)
    if isinstance(result, str):
        raise HTTPException(422, detail=result)
    return {
        "mode": result.mode,
        "feedback": result.text,
        "annotations": result.annotation_json,
    }


@app.get("/config")
def get_config():
    if _config is None:
        raise HTTPException(503, "Server not ready")
    data = asdict(_config)
    data.pop("api_key", None)   # never expose key
    return data


@app.put("/config")
def put_config(update: ConfigUpdate):
    if _config is None:
        raise HTTPException(503, "Server not ready")
    if update.model is not None:
        _config.model = update.model
    if update.api_base is not None:
        _config.api_base = update.api_base
    if update.custom_instructions is not None:
        _config.custom_instructions = update.custom_instructions
    if update.lookback_frames is not None:
        _config.lookback_frames = update.lookback_frames
    if update.style_focus is not None:
        _config.style_focus = update.style_focus
    _config.save()
    data = asdict(_config)
    data.pop("api_key", None)
    return data


# ---- Env override helper ------------------------------------------------

def _apply_env_overrides(cfg: LLMConfig) -> LLMConfig:
    model = os.environ.get("DRAWING_COACH_MODEL")
    key = os.environ.get("DRAWING_COACH_API_KEY")
    base = os.environ.get("DRAWING_COACH_API_BASE")
    if model:
        cfg.model = model
    if key:
        cfg.api_key = key
    if base:
        cfg.api_base = base
    return cfg
