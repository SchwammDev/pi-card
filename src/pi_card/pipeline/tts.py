from pathlib import Path
from typing import Protocol

from pi_card.hardware.audio_output import AudioOutput

TARGET_SAMPLE_RATE_HZ = 16_000
DEFAULT_VOICE_DIR = Path.home() / ".local/share/pi-card/voices"


class PiperVoice(Protocol):
    sample_rate: int

    def synthesize(self, text: str) -> bytes: ...


class PiperTTS:
    """Synthesises spoken text through a Piper voice and feeds the result
    into an AudioOutput as 16 kHz mono 16-bit PCM."""

    def __init__(self, *, voice: PiperVoice):
        self._voice = voice

    def speak(self, text: str, sink: AudioOutput) -> None:
        if not text:
            raise ValueError("text must not be empty")

        pcm = self._voice.synthesize(text)
        sink.play(_resample_to_target(pcm, self._voice.sample_rate))


def _resample_to_target(pcm: bytes, source_rate: int) -> bytes:
    if source_rate == TARGET_SAMPLE_RATE_HZ:
        return pcm

    import numpy as np

    source = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    if source.size == 0:
        return b""

    duration_s = source.size / source_rate
    target_size = int(round(duration_s * TARGET_SAMPLE_RATE_HZ))
    source_times = np.linspace(0.0, duration_s, num=source.size, endpoint=False)
    target_times = np.linspace(0.0, duration_s, num=target_size, endpoint=False)
    resampled = np.interp(target_times, source_times, source)
    return resampled.astype(np.int16).tobytes()


def load_piper_voice(
    voice_name: str, voice_dir: Path = DEFAULT_VOICE_DIR
) -> PiperVoice:
    """Build the production Piper voice. Downloads the model on first use.
    Imported lazily so tests don't require the piper package."""
    from piper.voice import PiperVoice as RealPiperVoice  # type: ignore[import-not-found]
    from piper.download_voices import download_voice  # type: ignore[import-not-found]

    voice_dir.mkdir(parents=True, exist_ok=True)
    model_path = voice_dir / f"{voice_name}.onnx"
    if not model_path.exists():
        download_voice(voice_name, voice_dir)

    real = RealPiperVoice.load(model_path)

    class _Adapter:
        sample_rate = int(real.config.sample_rate)

        def synthesize(self, text: str) -> bytes:
            chunks = [bytes(chunk.audio_int16_bytes) for chunk in real.synthesize(text)]
            return b"".join(chunks)

    return _Adapter()
