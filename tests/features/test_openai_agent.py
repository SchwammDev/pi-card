from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from pi_card.adapters.openai_agent import OpenAIAgent
from pi_card.hardware.ai_agent import Message


@dataclass
class FakeCompletions:
    chunks: list[SimpleNamespace]
    received_kwargs: dict = field(default_factory=dict)

    def create(self, **kwargs):
        self.received_kwargs = kwargs
        return iter(self.chunks)


@dataclass
class FakeChat:
    completions: FakeCompletions


@dataclass
class FakeClient:
    chat: FakeChat


def _delta_chunk(content: str | None) -> SimpleNamespace:
    delta = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _make_agent(
    chunks: list[SimpleNamespace], model: str = "gpt-test", extra_body=None
) -> tuple[OpenAIAgent, FakeCompletions]:
    completions = FakeCompletions(chunks=chunks)
    client = FakeClient(chat=FakeChat(completions=completions))
    return (
        OpenAIAgent(client=client, model=model, extra_body=extra_body),
        completions,
    )


def _drain(agent: OpenAIAgent, messages: list[Message]) -> list[str]:
    return list(agent.stream(messages))


def test_forwards_the_configured_model_name():
    agent, completions = _make_agent([_delta_chunk("hi")], model="my-model")

    _drain(agent, [Message(role="user", content="hi")])

    assert completions.received_kwargs["model"] == "my-model"


def test_maps_messages_to_openai_role_content_dicts():
    agent, completions = _make_agent([_delta_chunk("hi")])

    _drain(agent, [Message(role="system", content="be concise"), Message(role="user", content="hi")])

    assert completions.received_kwargs["messages"] == [
        {"role": "system", "content": "be concise"},
        {"role": "user", "content": "hi"},
    ]


def test_requests_a_streaming_response_so_chunks_arrive_incrementally():
    agent, completions = _make_agent([_delta_chunk("hi")])

    _drain(agent, [Message(role="user", content="hello")])

    assert completions.received_kwargs["stream"] is True


def test_yields_delta_content_in_order():
    chunks = [_delta_chunk("Hello"), _delta_chunk(", "), _delta_chunk("world.")]
    agent, _ = _make_agent(chunks)

    deltas = _drain(agent, [Message(role="user", content="hi")])

    assert deltas == ["Hello", ", ", "world."]


def test_skips_empty_or_missing_content_chunks_so_role_only_frames_do_not_corrupt_output():
    chunks = [_delta_chunk(None), _delta_chunk(""), _delta_chunk("text")]
    agent, _ = _make_agent(chunks)

    deltas = _drain(agent, [Message(role="user", content="hi")])

    assert deltas == ["text"]


def test_extra_body_is_omitted_when_unset_so_non_thinking_providers_are_unaffected():
    agent, completions = _make_agent([_delta_chunk("hi")])

    _drain(agent, [Message(role="user", content="hello")])

    assert "extra_body" not in completions.received_kwargs


def test_extra_body_is_forwarded_to_chat_completions_so_qwen_thinking_can_be_disabled():
    qwen_disable_thinking = {"chat_template_kwargs": {"enable_thinking": False}}
    agent, completions = _make_agent(
        [_delta_chunk("hi")], extra_body=qwen_disable_thinking
    )

    _drain(agent, [Message(role="user", content="hello")])

    assert completions.received_kwargs["extra_body"] == qwen_disable_thinking


def test_empty_message_list_is_rejected():
    agent, _ = _make_agent([_delta_chunk("unused")])

    with pytest.raises(ValueError):
        _drain(agent, [])
