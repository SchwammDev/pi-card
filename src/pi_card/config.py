from dataclasses import dataclass
from pathlib import Path

import yaml

from pi_card.pipeline.wake_word import DEFAULT_WAKE_WORD, SUPPORTED_WAKE_WORDS


class ConfigError(ValueError):
    """Raised when the config file is missing, malformed, or incomplete."""


REQUIRED_AGENT_FIELDS = ("base_url", "api_key", "model")


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    model: str
    language: str = "en"
    silence_timeout: float = 5.0
    max_stt_retries: int = 2
    wake_word: str = DEFAULT_WAKE_WORD

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

        return cls(
            base_url=agent["base_url"],
            api_key=agent["api_key"],
            model=agent["model"],
            language=raw.get("language", cls.language),
            silence_timeout=float(raw.get("silence_timeout", cls.silence_timeout)),
            max_stt_retries=int(raw.get("max_stt_retries", cls.max_stt_retries)),
            wake_word=wake_word,
        )
