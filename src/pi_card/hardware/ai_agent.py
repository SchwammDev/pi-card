from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Literal

Role = Literal["system", "user", "assistant"]


@dataclass
class Message:
    role: Role
    content: str | None = None


class AIAgent(ABC):
    @abstractmethod
    def stream(self, messages: list[Message]) -> Iterator[str]: ...
