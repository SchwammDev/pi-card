import logging
from typing import Iterator, Protocol

from pi_card.hardware.ai_agent import AIAgent, Message

_latency = logging.getLogger("pi_card.latency")


class _ChatCompletions(Protocol):
    def create(self, **kwargs): ...


class _Chat(Protocol):
    completions: _ChatCompletions


class _Client(Protocol):
    chat: _Chat


class OpenAIAgent(AIAgent):
    """AIAgent backed by any OpenAI chat-completions-compatible client.

    The client is injected so that provider choice, base_url, api_key, and
    transport settings live outside this class — and so that tests can drive
    it with a fake client."""

    def __init__(
        self,
        *,
        client: _Client,
        model: str,
        extra_body: dict | None = None,
    ):
        self._client = client
        self._model = model
        self._extra_body = extra_body

    def stream(self, messages: list[Message]) -> Iterator[str]:
        if not messages:
            raise ValueError("messages must not be empty")

        kwargs: dict = {
            "model": self._model,
            "messages": [_message_to_openai(m) for m in messages],
            "stream": True,
        }
        if self._extra_body is not None:
            kwargs["extra_body"] = self._extra_body

        _latency.info(
            "agent_call model=%s extra_body=%r", self._model, self._extra_body
        )
        for event in self._client.chat.completions.create(**kwargs):
            content = getattr(event.choices[0].delta, "content", None)
            if content:
                yield content


def _message_to_openai(message: Message) -> dict:
    return {"role": message.role, "content": message.content}


def load_openai_client(*, base_url: str, api_key: str):
    """Build the production OpenAI client. Imported lazily so tests don't
    require the openai package."""
    from openai import OpenAI  # type: ignore[import-not-found]

    return OpenAI(base_url=base_url, api_key=api_key)
