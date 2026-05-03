import textwrap

import pytest

from pi_card.config import Config, ConfigError


def _write_config(tmp_path, body: str):
    path = tmp_path / "config.yaml"
    path.write_text(textwrap.dedent(body))
    return path


def _load_with_overrides(tmp_path, **overrides) -> Config:
    lines = [
        "agent:",
        "  base_url: https://api.example.com/v1",
        "  api_key: secret",
        "  model: gpt-4o-mini",
    ]
    for key, value in overrides.items():
        lines.append(f"{key}: {value}")
    path = tmp_path / "config.yaml"
    path.write_text("\n".join(lines) + "\n")
    return Config.load(path)


def test_config_loads_all_required_fields(tmp_path):
    path = _write_config(
        tmp_path,
        """
        agent:
          base_url: https://api.example.com/v1
          api_key: secret
          model: gpt-4o-mini
        """,
    )

    config = Config.load(path)

    assert config.base_url == "https://api.example.com/v1"
    assert config.api_key == "secret"
    assert config.model == "gpt-4o-mini"


def test_config_applies_defaults_when_only_required_fields_provided(tmp_path):
    path = _write_config(
        tmp_path,
        """
        agent:
          base_url: https://api.example.com/v1
          api_key: secret
          model: gpt-4o-mini
        """,
    )

    config = Config.load(path)

    assert config.language == "en"
    assert config.silence_timeout == 5.0
    assert config.max_stt_retries == 2


def test_config_overrides_defaults_when_values_present(tmp_path):
    path = _write_config(
        tmp_path,
        """
        agent:
          base_url: https://api.example.com/v1
          api_key: secret
          model: gpt-4o-mini
        language: fr
        silence_timeout: 4.5
        max_stt_retries: 5
        """,
    )

    config = Config.load(path)

    assert config.language == "fr"
    assert config.silence_timeout == 4.5
    assert config.max_stt_retries == 5


@pytest.mark.parametrize("missing_field", ["base_url", "api_key", "model"])
def test_config_fails_fast_when_required_agent_field_is_missing(tmp_path, missing_field):
    agent_fields = {
        "base_url": "https://api.example.com/v1",
        "api_key": "secret",
        "model": "gpt-4o-mini",
    }
    del agent_fields[missing_field]
    body = "agent:\n" + "".join(f"  {k}: {v}\n" for k, v in agent_fields.items())
    path = tmp_path / "config.yaml"
    path.write_text(body)

    with pytest.raises(ConfigError) as excinfo:
        Config.load(path)

    assert missing_field in str(excinfo.value)


def test_config_fails_fast_when_agent_section_is_missing(tmp_path):
    path = _write_config(tmp_path, "language: en\n")

    with pytest.raises(ConfigError) as excinfo:
        Config.load(path)

    assert "agent" in str(excinfo.value)


def test_config_default_wake_word_is_computer(tmp_path):
    config = _load_with_overrides(tmp_path)

    assert config.wake_word == "computer"


def test_config_accepts_documented_wake_word_override(tmp_path):
    config = _load_with_overrides(tmp_path, wake_word="hey_jarvis")

    assert config.wake_word == "hey_jarvis"


def test_config_rejects_unknown_wake_word(tmp_path):
    with pytest.raises(ConfigError) as excinfo:
        _load_with_overrides(tmp_path, wake_word="not_a_real_wake_word")

    assert "not_a_real_wake_word" in str(excinfo.value)
    assert "computer" in str(excinfo.value)
    assert "hey_jarvis" in str(excinfo.value)


def test_config_default_min_silence_duration_is_long_enough_for_natural_pauses(tmp_path):
    config = _load_with_overrides(tmp_path)

    assert config.min_silence_duration_ms >= 1200


def test_config_overrides_min_silence_duration(tmp_path):
    config = _load_with_overrides(tmp_path, min_silence_duration_ms=2000)

    assert config.min_silence_duration_ms == 2000


def test_config_fails_fast_when_file_does_not_exist(tmp_path):
    with pytest.raises(ConfigError) as excinfo:
        Config.load(tmp_path / "does-not-exist.yaml")

    assert "does-not-exist.yaml" in str(excinfo.value)
