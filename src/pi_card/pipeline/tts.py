import queue
import threading
from pathlib import Path
from typing import Iterable, Iterator, Protocol

from pi_card.hardware.audio_output import AudioOutput

TARGET_SAMPLE_RATE_HZ = 16_000
DEFAULT_VOICE_DIR = Path.home() / ".local/share/pi-card/voices"


class TTSError(Exception):
    pass


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

    def speak_stream(
        self, texts: Iterable[str], sink: AudioOutput
    ) -> Iterator[str]:
        audio_queue: queue.Queue = queue.Queue(maxsize=1)
        stop = threading.Event()

        producer = threading.Thread(
            target=_synth_into_queue,
            args=(self._voice, texts, audio_queue, stop),
            daemon=True,
        )
        producer.start()

        try:
            yield from _drain_queue_into_sink(audio_queue, sink)
        finally:
            stop.set()
            _drain_remaining(audio_queue)
            producer.join(timeout=2.0)


_DONE = ("done", None, None)


def _synth_into_queue(voice, texts, audio_queue, stop):
    try:
        for text in texts:
            if stop.is_set():
                return
            if not text:
                continue
            try:
                pcm = voice.synthesize(text)
            except Exception as exc:
                _put_until_stopped(audio_queue, ("synth_error", exc, None), stop)
                return
            audio = _resample_to_target(pcm, voice.sample_rate)
            if not _put_until_stopped(audio_queue, ("audio", text, audio), stop):
                return
    except Exception as exc:
        _put_until_stopped(audio_queue, ("source_error", exc, None), stop)
        return
    _put_until_stopped(audio_queue, _DONE, stop)


def _put_until_stopped(audio_queue, item, stop) -> bool:
    while not stop.is_set():
        try:
            audio_queue.put(item, timeout=0.1)
            return True
        except queue.Full:
            continue
    return False


def _drain_queue_into_sink(audio_queue, sink) -> Iterator[str]:
    while True:
        kind, payload, audio = audio_queue.get()
        if kind == "done":
            return
        if kind == "synth_error":
            raise TTSError(str(payload)) from payload
        if kind == "source_error":
            raise payload
        try:
            sink.play(audio)
        except Exception as exc:
            raise TTSError(str(exc)) from exc
        yield payload


def _drain_remaining(audio_queue) -> None:
    try:
        while True:
            audio_queue.get_nowait()
    except queue.Empty:
        pass


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
