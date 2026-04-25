from typing import Protocol

SAMPLE_RATE_HZ = 16_000
SAMPLE_WIDTH_BYTES = 2
_INT16_FULL_SCALE = 32_768.0


class WhisperModel(Protocol):
    def transcribe(self, audio, language: str, **kwargs): ...


class WhisperSTT:
    """Adapts raw 16 kHz mono PCM bytes to a Faster-Whisper model and
    concatenates the segments into a single transcript."""

    def __init__(self, *, model: WhisperModel):
        self._model = model

    def transcribe(self, pcm: bytes, language: str) -> str:
        if len(pcm) % SAMPLE_WIDTH_BYTES != 0:
            raise ValueError(
                f"pcm length {len(pcm)} is not a multiple of {SAMPLE_WIDTH_BYTES} bytes"
            )

        import numpy as np

        samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
        samples /= _INT16_FULL_SCALE

        segments, _info = self._model.transcribe(samples, language=language, vad_filter=True)
        return "".join(segment.text for segment in segments).strip()


def load_faster_whisper_model(
    model_size: str = "base", compute_type: str = "int8"
) -> WhisperModel:
    """Build the production Faster-Whisper model. Imported lazily so tests
    don't require the faster_whisper package."""
    from faster_whisper import WhisperModel as FasterWhisperModel  # type: ignore[import-not-found]

    return FasterWhisperModel(model_size, compute_type=compute_type)
