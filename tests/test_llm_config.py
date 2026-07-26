"""Unit tests for LLMConfig — plain dataclass behaviour."""

from drawing_coach.llm_config import LLMConfig


def test_is_configured_false_when_empty():
    cfg = LLMConfig()
    assert not cfg.is_configured()


def test_is_configured_true_when_model_set():
    cfg = LLMConfig(model="gpt-4o")
    assert cfg.is_configured()


def test_defaults():
    cfg = LLMConfig()
    assert cfg.model == ""
    assert cfg.api_base == ""
    assert cfg.api_key == ""
    assert cfg.capture_interval == 30
    assert cfg.hotkey == "<ctrl>+<shift>+f"
    assert cfg.stuck_threshold == 10.0
    assert cfg.stuck_consecutive == 3
    assert cfg.stuck_cooldown_minutes == 5
    assert cfg.lookback_frames == 2
    assert cfg.dedup_threshold == 2.0
    assert cfg.history_retention_sessions == 10
    assert cfg.style_focus == ""
    assert cfg.style_focus_is_preset is True
    assert cfg.memory_resummarize_interval == 20
    assert cfg.memory_max_observations == 200
    assert cfg.memory_summary_history_max == 200


def test_field_assignment():
    cfg = LLMConfig(model="gpt-4o", api_key="sk-test", capture_interval=60)
    assert cfg.model == "gpt-4o"
    assert cfg.api_key == "sk-test"
    assert cfg.capture_interval == 60


def test_effective_style_label_general_when_empty():
    cfg = LLMConfig()
    assert cfg.effective_style_label() == "General"


def test_effective_style_label_returns_focus():
    cfg = LLMConfig(style_focus="Anime/Manga")
    assert cfg.effective_style_label() == "Anime/Manga"


def test_style_prompt_fragment_empty_when_no_focus():
    cfg = LLMConfig()
    assert cfg.style_prompt_fragment() == ""


def test_style_prompt_fragment_preset():
    cfg = LLMConfig(style_focus="Line Drawing", style_focus_is_preset=True)
    fragment = cfg.style_prompt_fragment()
    assert "Line Drawing" in fragment
    assert "practising" in fragment


def test_style_prompt_fragment_custom():
    cfg = LLMConfig(style_focus="gothic pokemon", style_focus_is_preset=False)
    fragment = cfg.style_prompt_fragment()
    assert "gothic pokemon" in fragment
    assert "focusing on" in fragment
