"""Integration tests for the headless FastAPI server."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from drawing_coach import server as srv
from drawing_coach.capture_engine import CapturedFrame
from drawing_coach.feedback_engine import FeedbackResponse
from drawing_coach.llm_config import LLMConfig


def _setup(monkeypatch):
    """Wire up lightweight mocks and return a TestClient."""
    cfg = LLMConfig(model="gpt-4o")
    capture = MagicMock()
    capture.target = MagicMock(title="Paint")
    capture.get_frames.return_value = [
        CapturedFrame(image=Image.new("RGB", (100, 100)), timestamp=datetime.now(), path=Path("/tmp/f.png"))
    ]
    capture.capture_once.return_value = CapturedFrame(
        image=Image.new("RGB", (100, 100)), timestamp=datetime.now(), path=Path("/tmp/f.png")
    )
    feedback = MagicMock()
    feedback.request_feedback.return_value = FeedbackResponse(mode="quick_hint", text="Nice work!")

    monkeypatch.setattr(srv, "_config", cfg)
    monkeypatch.setattr(srv, "_capture", capture)
    monkeypatch.setattr(srv, "_feedback", feedback)
    return TestClient(srv.app)


def test_health(monkeypatch):
    client = _setup(monkeypatch)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_capture_success(monkeypatch):
    client = _setup(monkeypatch)
    resp = client.post("/capture")
    assert resp.status_code == 200
    assert "timestamp" in resp.json()


def test_capture_no_window(monkeypatch):
    client = _setup(monkeypatch)
    srv._capture.target = None
    resp = client.post("/capture")
    assert resp.status_code == 422


def test_feedback_success(monkeypatch):
    client = _setup(monkeypatch)
    resp = client.post("/feedback", json={"mode": "quick_hint"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "quick_hint"
    assert "feedback" in body


def test_feedback_no_frames(monkeypatch):
    client = _setup(monkeypatch)
    srv._capture.get_frames.return_value = []
    srv._feedback.request_feedback.return_value = "No frames captured yet"
    resp = client.post("/feedback")
    assert resp.status_code == 422


def test_get_config_excludes_api_key(monkeypatch):
    client = _setup(monkeypatch)
    resp = client.get("/config")
    assert resp.status_code == 200
    assert "api_key" not in resp.json()
    assert "model" in resp.json()


def test_put_config_updates_model(monkeypatch):
    client = _setup(monkeypatch)
    resp = client.put("/config", json={"model": "claude-3-5-sonnet-20241022"})
    assert resp.status_code == 200
    assert srv._config.model == "claude-3-5-sonnet-20241022"
    assert "api_key" not in resp.json()
