from typing import Protocol

from pi_card.hardware.audio_input import AudioInput


class WakeWordEngine(Protocol):
    def predict(self, frame: bytes) -> dict[str, float]: ...


DEFAULT_WAKE_WORD = "hey_jarvis"
DEFAULT_THRESHOLD = 0.5


class WakeWordDetector:
    """Single-shot wake-word detector. Consumes an AudioInput until the
    configured wake-word's score crosses the threshold, then returns."""

    def __init__(
        self,
        *,
        engine: WakeWordEngine,
        model_name: str = DEFAULT_WAKE_WORD,
        threshold: float = DEFAULT_THRESHOLD,
    ):
        self._engine = engine
        self._model_name = model_name
        self._threshold = threshold

    def wait_for_wake_word(self, audio_in: AudioInput) -> None:
        while True:
            frame = audio_in.read_frame()
            scores = self._engine.predict(frame)
            if scores.get(self._model_name, 0.0) >= self._threshold:
                return


def load_openwakeword_engine(model_name: str = DEFAULT_WAKE_WORD) -> WakeWordEngine:
    """Build the production openWakeWord engine. Imported lazily so tests
    don't require the openwakeword package."""
    from openwakeword.model import Model  # type: ignore[import-not-found]
    import numpy as np

    model = Model(wakeword_models=[model_name])

    class _Adapter:
        def predict(self, frame: bytes) -> dict[str, float]:
            samples = np.frombuffer(frame, dtype=np.int16)
            return dict(model.predict(samples))

    return _Adapter()
