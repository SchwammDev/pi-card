from collections import deque


class FakeWakeWordEngine:
    """Returns pre-scripted detection scores, one dict per frame of audio."""

    def __init__(self, model_name: str = "computer", scores: list[float] | None = None):
        self._model_name = model_name
        self._scores: deque[float] = deque(scores or [])
        self.frames_seen: list[bytes] = []

    def queue_score(self, score: float) -> None:
        self._scores.append(score)

    def predict(self, frame: bytes) -> dict[str, float]:
        self.frames_seen.append(frame)
        score = self._scores.popleft() if self._scores else 0.0
        return {self._model_name: score}
