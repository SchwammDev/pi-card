"""The OpenAI agent is a thin translator between our Message dataclass and
the OpenAI chat-completions wire shape. These tests exercise that mapping
against an injected fake client — no network, no real SDK required."""

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from pi_card.adapters.openai_agent import OpenAIAgent
from pi_card.hardware.ai_agent import Message, ToolCall


@dataclass
class FakeCompletions:
    response: SimpleNamespace
    received_kwargs: dict = field(default_factory=dict)

    def create(self, **kwargs):
        self.received_kwargs = kwargs
        return self.response


@dataclass
class FakeChat:
    completions: FakeCompletions


@dataclass
class FakeClient:
    chat: FakeChat


def _assistant_response(content: str, tool_calls=None) -> SimpleNamespace:
    message = SimpleNamespace(role="assistant", content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _make_agent(response: SimpleNamespace, model: str = "gpt-test") -> tuple[OpenAIAgent, FakeCompletions]:
    completions = FakeCompletions(response=response)
    client = FakeClient(chat=FakeChat(completions=completions))
    return OpenAIAgent(client=client, model=model), completions


def test_sends_model_and_maps_simple_messages_to_openai_shape():
    agent, completions = _make_agent(_assistant_response("hi there"), model="my-model")

    agent.chat(
        [
            Message(role="system", content="be concise"),
            Message(role="user", content="hello"),
        ]
    )

    assert completions.received_kwargs["model"] == "my-model"
    assert completions.received_kwargs["messages"] == [
        {"role": "system", "content": "be concise"},
        {"role": "user", "content": "hello"},
    ]


def test_returns_assistant_reply_as_message():
    agent, _ = _make_agent(_assistant_response("sunny and warm"))

    reply = agent.chat([Message(role="user", content="weather?")])

    assert reply == Message(role="assistant", content="sunny and warm")


def test_serialises_tool_calls_on_outgoing_messages():
    agent, completions = _make_agent(_assistant_response("done"))

    agent.chat(
        [
            Message(
                role="assistant",
                content=None,
                tool_calls=[ToolCall(id="call_1", name="get_time", arguments='{"tz":"UTC"}')],
            ),
            Message(role="tool", tool_call_id="call_1", name="get_time", content="12:00"),
        ]
    )

    assert completions.received_kwargs["messages"] == [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "get_time", "arguments": '{"tz":"UTC"}'},
                }
            ],
        },
        {
            "role": "tool",
            "content": "12:00",
            "tool_call_id": "call_1",
            "name": "get_time",
        },
    ]


def test_parses_tool_calls_on_incoming_reply():
    tool_call = SimpleNamespace(
        id="call_42",
        function=SimpleNamespace(name="lookup", arguments='{"q":"x"}'),
    )
    agent, _ = _make_agent(_assistant_response(None, tool_calls=[tool_call]))

    reply = agent.chat([Message(role="user", content="look it up")])

    assert reply.role == "assistant"
    assert reply.content is None
    assert reply.tool_calls == [ToolCall(id="call_42", name="lookup", arguments='{"q":"x"}')]


def test_empty_message_list_is_rejected():
    agent, _ = _make_agent(_assistant_response("unused"))

    with pytest.raises(ValueError):
        agent.chat([])
