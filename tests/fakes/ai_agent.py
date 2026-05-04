from collections import deque
from typing import Iterator

from pi_card.hardware.ai_agent import AIAgent, Message


class FakeAIAgent(AIAgent):
    def __init__(self, responses: list[str | list[str]] | None = None):
        self._responses: deque[list[str]] = deque(
            self._as_deltas(r) for r in (responses or [])
        )
        self.received: list[list[Message]] = []
        self.deltas_yielded_for_active_reply = 0

    def queue(self, response: str | list[str]) -> None:
        self._responses.append(self._as_deltas(response))

    def stream(self, messages: list[Message]) -> Iterator[str]:
        self.received.append(list(messages))
        if not self._responses:
            raise AssertionError("FakeAIAgent has no queued response")
        deltas = self._responses.popleft()
        self.deltas_yielded_for_active_reply = 0
        for delta in deltas:
            self.deltas_yielded_for_active_reply += 1
            yield delta

    @staticmethod
    def _as_deltas(response: str | list[str]) -> list[str]:
        if isinstance(response, list):
            return list(response)
        return [response]
