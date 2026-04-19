from typing import Protocol

from pi_card.hardware.ai_agent import AIAgent, Message, ToolCall


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

    def __init__(self, *, client: _Client, model: str):
        self._client = client
        self._model = model

    def chat(self, messages: list[Message]) -> Message:
        if not messages:
            raise ValueError("messages must not be empty")

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[_message_to_openai(m) for m in messages],
        )
        return _openai_to_message(response.choices[0].message)


def _message_to_openai(message: Message) -> dict:
    payload: dict = {"role": message.role, "content": message.content}
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": tc.arguments},
            }
            for tc in message.tool_calls
        ]
    if message.tool_call_id is not None:
        payload["tool_call_id"] = message.tool_call_id
    if message.name is not None:
        payload["name"] = message.name
    return payload


def _openai_to_message(raw) -> Message:
    tool_calls: list[ToolCall] = []
    for tc in getattr(raw, "tool_calls", None) or []:
        tool_calls.append(
            ToolCall(id=tc.id, name=tc.function.name, arguments=tc.function.arguments)
        )
    return Message(
        role=getattr(raw, "role", "assistant"),
        content=getattr(raw, "content", None),
        tool_calls=tool_calls,
    )


def load_openai_client(*, base_url: str, api_key: str):
    """Build the production OpenAI client. Imported lazily so tests don't
    require the openai package."""
    from openai import OpenAI  # type: ignore[import-not-found]

    return OpenAI(base_url=base_url, api_key=api_key)
