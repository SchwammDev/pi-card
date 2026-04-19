from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON-encoded, OpenAI chat-completions shape


@dataclass
class Message:
    role: Role
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


class AIAgent(ABC):
    @abstractmethod
    def chat(self, messages: list[Message]) -> Message:
        """Send a conversation and return the assistant's next message."""
