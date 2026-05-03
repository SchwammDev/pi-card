from typing import Protocol

import numpy as np

SILERO_WINDOW_SAMPLES = 512
SILERO_WINDOW_BYTES = SILERO_WINDOW_SAMPLES * 2
INT16_MAX = 32768.0
DEFAULT_THRESHOLD = 0.5


class SpeechDetector(Protocol):
    def is_speech(self, frame: bytes) -> bool: ...

    def reset(self) -> None: ...


class SileroBackend(Protocol):
    def infer(self, samples: np.ndarray) -> float: ...

    def reset(self) -> None: ...


class SileroSpeechDetector:
    def __init__(self, backend: SileroBackend, threshold: float = DEFAULT_THRESHOLD):
        self._backend = backend
        self._threshold = threshold
        self._buffer = bytearray()

    def is_speech(self, frame: bytes) -> bool:
        self._buffer.extend(frame)
        crossed_threshold = False
        while len(self._buffer) >= SILERO_WINDOW_BYTES:
            window = self._drain_one_window()
            if self._backend.infer(window) >= self._threshold:
                crossed_threshold = True
        return crossed_threshold

    def reset(self) -> None:
        self._buffer.clear()
        self._backend.reset()

    def _drain_one_window(self) -> np.ndarray:
        raw = bytes(self._buffer[:SILERO_WINDOW_BYTES])
        del self._buffer[:SILERO_WINDOW_BYTES]
        return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / INT16_MAX
