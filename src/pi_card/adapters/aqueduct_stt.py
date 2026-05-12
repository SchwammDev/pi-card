import io
import wave
from typing import Protocol

from pi_card.pipeline.stt import SAMPLE_RATE_HZ, SAMPLE_WIDTH_BYTES, Transcript

WAV_FILENAME = "speech.wav"
WAV_CONTENT_TYPE = "audio/wav"
MONO_CHANNELS = 1


class _Transcriptions(Protocol):
    def create(self, **kwargs): ...


class _Audio(Protocol):
    transcriptions: _Transcriptions


class _Client(Protocol):
    audio: _Audio


class AqueductWhisperSTT:
    def __init__(self, *, client: _Client, model: str):
        self._client = client
        self._model = model

    def transcribe(self, pcm: bytes, language: str) -> Transcript:
        if len(pcm) % SAMPLE_WIDTH_BYTES != 0:
            raise ValueError(
                f"pcm length {len(pcm)} is not a multiple of {SAMPLE_WIDTH_BYTES} bytes"
            )

        wav_bytes = _pcm_to_wav(pcm)
        result = self._client.audio.transcriptions.create(
            model=self._model,
            file=(WAV_FILENAME, wav_bytes, WAV_CONTENT_TYPE),
            language=language,
        )
        return Transcript(text=result.text.strip(), avg_logprob=None)


def _pcm_to_wav(pcm: bytes) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(MONO_CHANNELS)
        writer.setsampwidth(SAMPLE_WIDTH_BYTES)
        writer.setframerate(SAMPLE_RATE_HZ)
        writer.writeframes(pcm)
    return buffer.getvalue()
