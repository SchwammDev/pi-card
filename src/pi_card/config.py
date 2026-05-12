from dataclasses import dataclass
from pathlib import Path

import yaml

from pi_card.pipeline.wake_word import (
    DEFAULT_THRESHOLD,
    DEFAULT_WAKE_WORD,
    SUPPORTED_WAKE_WORDS,
)


class ConfigError(ValueError):
    """Raised when the config file is missing, malformed, or incomplete."""


REQUIRED_AGENT_FIELDS = ("base_url", "api_key", "model")

LOCAL_STT_PROVIDER = "local"
AQUEDUCT_STT_PROVIDER = "aqueduct"
SUPPORTED_STT_PROVIDERS = (LOCAL_STT_PROVIDER, AQUEDUCT_STT_PROVIDER)


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    model: str
    language: str = "en"
    silence_timeout: float = 5.0
    max_stt_retries: int = 2
    wake_word: str = DEFAULT_WAKE_WORD
    wake_word_threshold: float = DEFAULT_THRESHOLD
    min_silence_duration_ms: int = 2500
    extra_body: dict | None = None
    stt_provider: str = LOCAL_STT_PROVIDER
    stt_model: str | None = None

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        path = Path(path)
        if not path.exists():
            raise ConfigError(f"Config file not found: {path}")

        raw = yaml.safe_load(path.read_text()) or {}
        if not isinstance(raw, dict):
            raise ConfigError(f"Config file {path} must contain a YAML mapping")

        agent = raw.get("agent")
        if not isinstance(agent, dict):
            raise ConfigError(
                f"Config file {path} is missing the required 'agent' section"
            )

        missing = [f for f in REQUIRED_AGENT_FIELDS if not agent.get(f)]
        if missing:
            fields = ", ".join(missing)
            raise ConfigError(
                f"Config file {path} is missing required agent field(s): {fields}"
            )

        wake_word = raw.get("wake_word", cls.wake_word)
        if wake_word not in SUPPORTED_WAKE_WORDS:
            supported = ", ".join(sorted(SUPPORTED_WAKE_WORDS))
            raise ConfigError(
                f"Config file {path} sets wake_word={wake_word!r}; "
                f"supported values: {supported}"
            )

        wake_word_threshold = _parse_wake_word_threshold(
            raw.get("wake_word_threshold", cls.wake_word_threshold), path
        )

        extra_body = raw.get("extra_body")
        if extra_body is not None and not isinstance(extra_body, dict):
            raise ConfigError(
                f"Config file {path} has 'extra_body' but it is not a YAML mapping"
            )

        stt_provider, stt_model = _parse_stt_section(raw.get("stt"), path)

        return cls(
            base_url=agent["base_url"],
            api_key=agent["api_key"],
            model=agent["model"],
            language=raw.get("language", cls.language),
            silence_timeout=float(raw.get("silence_timeout", cls.silence_timeout)),
            max_stt_retries=int(raw.get("max_stt_retries", cls.max_stt_retries)),
            wake_word=wake_word,
            wake_word_threshold=wake_word_threshold,
            min_silence_duration_ms=int(
                raw.get("min_silence_duration_ms", cls.min_silence_duration_ms)
            ),
            extra_body=extra_body,
            stt_provider=stt_provider,
            stt_model=stt_model,
        )


def _parse_wake_word_threshold(raw, path: Path) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ConfigError(
            f"Config file {path} has 'wake_word_threshold' but it is not a number"
        )
    if not 0.0 < value <= 1.0:
        raise ConfigError(
            f"Config file {path} sets wake_word_threshold={value}; "
            f"must be in the range (0.0, 1.0]"
        )
    return value


def _parse_stt_section(raw_stt, path: Path) -> tuple[str, str | None]:
    if raw_stt is None:
        return LOCAL_STT_PROVIDER, None
    if not isinstance(raw_stt, dict):
        raise ConfigError(
            f"Config file {path} has 'stt' but it is not a YAML mapping"
        )

    provider = raw_stt.get("provider", LOCAL_STT_PROVIDER)
    if provider not in SUPPORTED_STT_PROVIDERS:
        supported = ", ".join(SUPPORTED_STT_PROVIDERS)
        raise ConfigError(
            f"Config file {path} sets stt.provider={provider!r}; "
            f"supported values: {supported}"
        )

    model = raw_stt.get("model")
    if provider == AQUEDUCT_STT_PROVIDER and not model:
        raise ConfigError(
            f"Config file {path} sets stt.provider=aqueduct but is missing stt.model "
            f"(e.g. whisper-large-v3-turbo)"
        )

    return provider, model
