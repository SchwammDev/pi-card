from pathlib import Path
from typing import Protocol

import numpy as np

SILERO_WINDOW_SAMPLES = 512
SILERO_WINDOW_BYTES = SILERO_WINDOW_SAMPLES * 2
SILERO_CONTEXT_SAMPLES = 64
SILERO_STATE_SHAPE = (2, 1, 128)
SILERO_SAMPLE_RATE = 16_000
INT16_MAX = 32768.0
DEFAULT_THRESHOLD = 0.5
DEFAULT_SILERO_MODEL_PATH = Path.home() / ".local/share/pi-card/silero_vad.onnx"


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


def load_silero_speech_detector(
    model_path: Path = DEFAULT_SILERO_MODEL_PATH,
    threshold: float = DEFAULT_THRESHOLD,
) -> SileroSpeechDetector:
    import onnxruntime  # type: ignore[import-not-found]

    session = onnxruntime.InferenceSession(
        str(model_path),
        providers=["CPUExecutionProvider"],
    )
    return SileroSpeechDetector(_OnnxSileroBackend(session), threshold=threshold)


class _OnnxSileroBackend:
    _SR = np.array(SILERO_SAMPLE_RATE, dtype=np.int64)

    def __init__(self, session):
        self._session = session
        self.reset()

    def reset(self) -> None:
        self._state = np.zeros(SILERO_STATE_SHAPE, dtype=np.float32)
        self._context = np.zeros((1, SILERO_CONTEXT_SAMPLES), dtype=np.float32)

    def infer(self, samples: np.ndarray) -> float:
        window = samples.reshape(1, -1)
        x = np.concatenate([self._context, window], axis=1)
        out, self._state = self._session.run(
            None,
            {"input": x, "state": self._state, "sr": self._SR},
        )
        self._context = x[:, -SILERO_CONTEXT_SAMPLES:]
        return float(out[0][0])
