from collections import deque

from pi_card.hardware.ai_agent import AIAgent, Message


class FakeAIAgent(AIAgent):
    """Returns canned assistant messages in order. Records received conversations."""

    def __init__(self, responses: list[Message | str] | None = None):
        self._responses: deque[Message] = deque(
            self._as_message(r) for r in (responses or [])
        )
        self.received: list[list[Message]] = []

    def queue(self, response: Message | str) -> None:
        self._responses.append(self._as_message(response))

    def chat(self, messages: list[Message]) -> Message:
        self.received.append(list(messages))
        if not self._responses:
            raise AssertionError("FakeAIAgent has no queued response")
        return self._responses.popleft()

    @staticmethod
    def _as_message(response: Message | str) -> Message:
        if isinstance(response, Message):
            return response
        return Message(role="assistant", content=response)
