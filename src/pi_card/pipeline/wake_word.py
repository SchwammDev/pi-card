from pathlib import Path
from typing import Protocol

from pi_card.hardware.audio_input import AudioInput


class WakeWordEngine(Protocol):
    def predict(self, frame: bytes) -> dict[str, float]: ...

    def reset(self) -> None: ...


DEFAULT_WAKE_WORD = "computer"
DEFAULT_THRESHOLD = 0.5
DEFAULT_MODEL_DIR = Path.home() / ".local/share/pi-card/wake-words"

WAKE_WORD_MODEL_URLS = {
    "computer": (
        "https://raw.githubusercontent.com/fwartner/"
        "home-assistant-wakewords-collection/"
        "63f57e400c0c131d8a6eb9135d071d6f0f165c28/en/computer/computer_v2.tflite"
    ),
}


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
        self._engine.reset()
        while True:
            frame = audio_in.read_frame()
            scores = self._engine.predict(frame)
            if scores.get(self._model_name, 0.0) >= self._threshold:
                return


def load_openwakeword_engine(
    model_name: str = DEFAULT_WAKE_WORD,
    model_dir: Path = DEFAULT_MODEL_DIR,
) -> WakeWordEngine:
    """Build the production openWakeWord engine. Imported lazily so tests
    don't require the openwakeword package."""
    from openwakeword.model import Model  # type: ignore[import-not-found]
    from openwakeword.utils import download_models  # type: ignore[import-not-found]
    import numpy as np

    download_models()
    model_path = _ensure_wake_word_model(model_name, model_dir)

    model = Model(wakeword_models=[str(model_path)])

    class _Adapter:
        def predict(self, frame: bytes) -> dict[str, float]:
            samples = np.frombuffer(frame, dtype=np.int16)
            return dict(model.predict(samples))

        def reset(self) -> None:
            model.reset()

    return _Adapter()


def _ensure_wake_word_model(model_name: str, model_dir: Path) -> Path:
    if model_name not in WAKE_WORD_MODEL_URLS:
        raise ValueError(
            f"No download URL configured for wake-word model {model_name!r}. "
            f"Known models: {sorted(WAKE_WORD_MODEL_URLS)}"
        )
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / f"{model_name}.tflite"
    if not model_path.exists():
        _download_to(WAKE_WORD_MODEL_URLS[model_name], model_path)
    return model_path


def _download_to(url: str, destination: Path) -> None:
    import urllib.request

    tmp_path = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(url) as response, tmp_path.open("wb") as out:
        while chunk := response.read(64 * 1024):
            out.write(chunk)
    tmp_path.replace(destination)
