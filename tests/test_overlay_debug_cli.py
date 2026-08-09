import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import litellm
import pytest
from PIL import Image

SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "overlay_debug_cli.py"

spec = importlib.util.spec_from_file_location("overlay_debug_cli", SCRIPT_PATH)
overlay_debug_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overlay_debug_cli)


def _fake_response(content: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


@pytest.fixture(autouse=True)
def configured_env(monkeypatch):
    monkeypatch.setenv("DRAWING_COACH_MODEL", "fake/test-model")
    monkeypatch.setenv("DRAWING_COACH_API_KEY", "fake-key")


@pytest.fixture
def image_path(tmp_path) -> Path:
    p = tmp_path / "frame.png"
    Image.new("RGB", (200, 150), color=(255, 255, 255)).save(p)
    return p


def test_dump_defaults_writes_prompt_and_schema(tmp_path, capsys):
    out_dir = tmp_path / "work"
    code = overlay_debug_cli.main(["--dump-defaults", str(out_dir)])

    assert code == 0
    assert (out_dir / "prompt.txt").read_text()
    schema = json.loads((out_dir / "schema.json").read_text())
    assert schema["json_schema"]["name"] == "coaching_feedback"
    printed = json.loads(capsys.readouterr().out)
    assert printed["ok"] is True


def test_missing_image_argument_errors(capsys):
    with pytest.raises(SystemExit) as exc_info:
        overlay_debug_cli.main([])
    assert exc_info.value.code == 2


def test_image_not_found_returns_exit_2_with_json_error(tmp_path, capsys):
    code = overlay_debug_cli.main([str(tmp_path / "missing.png")])
    assert code == 2
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is False
    assert "Could not open image" in result["error"]


def test_malformed_schema_file_returns_exit_2(tmp_path, image_path, capsys):
    schema_file = tmp_path / "schema.json"
    schema_file.write_text("{not valid json")

    code = overlay_debug_cli.main([str(image_path), "--schema-file", str(schema_file)])

    assert code == 2
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is False
    assert "not valid JSON" in result["error"]


def test_invalid_character_bbox_returns_exit_2(image_path, capsys):
    code = overlay_debug_cli.main([str(image_path), "--character-bbox", "1,2,3"])
    assert code == 2
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is False


def test_successful_run_exits_0_and_prints_result(monkeypatch, image_path, capsys):
    payload = json.dumps({"feedback_text": "ok", "observations": [], "annotations": []})
    monkeypatch.setattr(litellm, "completion", lambda **kw: _fake_response(payload))

    code = overlay_debug_cli.main([str(image_path), "--pretty"])

    assert code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is True
    assert result["warning"] is None


def test_unparseable_response_exits_1(monkeypatch, image_path, capsys):
    monkeypatch.setattr(litellm, "completion", lambda **kw: _fake_response("not json"))

    code = overlay_debug_cli.main([str(image_path)])

    assert code == 1
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is True
    assert result["warning"]


def test_out_file_receives_same_json_as_stdout(
    monkeypatch, image_path, tmp_path, capsys
):
    payload = json.dumps({"feedback_text": "ok", "observations": [], "annotations": []})
    monkeypatch.setattr(litellm, "completion", lambda **kw: _fake_response(payload))
    out_file = tmp_path / "result.json"

    overlay_debug_cli.main([str(image_path), "--out", str(out_file)])

    stdout = capsys.readouterr().out.strip()
    assert out_file.read_text() == stdout


def test_custom_prompt_file_is_used(monkeypatch, image_path, tmp_path, capsys):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("a very specific custom prompt")
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _fake_response(json.dumps({"feedback_text": "ok", "annotations": []}))

    monkeypatch.setattr(litellm, "completion", fake_completion)

    overlay_debug_cli.main([str(image_path), "--prompt-file", str(prompt_file)])

    assert captured["messages"][0]["content"] == "a very specific custom prompt"
