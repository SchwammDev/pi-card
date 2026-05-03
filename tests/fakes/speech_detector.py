from collections import deque

import numpy as np


class FakeSileroBackend:
    def __init__(self, probabilities: list[float] | None = None):
        self._scripted: deque[float] = deque(probabilities or [])
        self.windows_seen: list[np.ndarray] = []
        self.reset_call_count = 0

    def queue(self, *probs: float) -> None:
        for p in probs:
            self._scripted.append(p)

    def infer(self, samples: np.ndarray) -> float:
        self.windows_seen.append(samples.copy())
        return self._scripted.popleft() if self._scripted else 0.0

    def reset(self) -> None:
        self.reset_call_count += 1


class ScriptedSpeechDetector:
    def __init__(self, results: list[bool] | None = None):
        self._results: deque[bool] = deque(results or [])
        self.frames_seen: list[bytes] = []
        self.reset_call_count = 0

    def queue(self, *values: bool) -> None:
        for v in values:
            self._results.append(v)

    def is_speech(self, frame: bytes) -> bool:
        self.frames_seen.append(frame)
        return self._results.popleft() if self._results else False

    def reset(self) -> None:
        self.reset_call_count += 1
