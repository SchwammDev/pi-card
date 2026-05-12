import io
import wave
from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from pi_card.adapters.aqueduct_stt import AqueductWhisperSTT


@dataclass
class FakeTranscriptions:
    text: str = ""
    received_kwargs: dict = field(default_factory=dict)

    def create(self, **kwargs):
        self.received_kwargs = dict(kwargs)
        return SimpleNamespace(text=self.text)


@dataclass
class FakeAudio:
    transcriptions: FakeTranscriptions


@dataclass
class FakeClient:
    audio: FakeAudio


def _silent_pcm(seconds: float, sample_rate: int = 16_000) -> bytes:
    return b"\x00\x00" * int(seconds * sample_rate)


def _make_stt(text: str = "", model: str = "whisper-large-v3-turbo"):
    transcriptions = FakeTranscriptions(text=text)
    client = FakeClient(audio=FakeAudio(transcriptions=transcriptions))
    return AqueductWhisperSTT(client=client, model=model), transcriptions


def _uploaded_file_bytes(transcriptions: FakeTranscriptions) -> bytes:
    file_arg = transcriptions.received_kwargs["file"]
    if isinstance(file_arg, tuple):
        return file_arg[1]
    return file_arg.read()


PIPELINE_AUDIO_FORMAT = (1, 2, 16_000)


def assert_wav_carries_pcm_at_pipeline_format(wav_bytes: bytes, pcm: bytes) -> None:
    with wave.open(io.BytesIO(wav_bytes), "rb") as w:
        samples = w.readframes(w.getnframes())
        format_triple = (w.getnchannels(), w.getsampwidth(), w.getframerate())
    assert samples == pcm
    assert format_triple == PIPELINE_AUDIO_FORMAT


def test_returns_the_trimmed_transcript_text_from_the_remote_response():
    stt, _ = _make_stt(text="   hello world   ")

    assert stt.transcribe(_silent_pcm(0.5), language="en").text == "hello world"


def test_forwards_the_requested_language_to_the_remote_endpoint():
    stt, transcriptions = _make_stt()

    stt.transcribe(_silent_pcm(0.5), language="fr")

    assert transcriptions.received_kwargs["language"] == "fr"


def test_forwards_the_configured_whisper_model_name():
    stt, transcriptions = _make_stt(model="whisper-large-v3-turbo")

    stt.transcribe(_silent_pcm(0.5), language="en")

    assert transcriptions.received_kwargs["model"] == "whisper-large-v3-turbo"


def test_supports_switching_language_between_calls():
    stt, transcriptions = _make_stt()

    stt.transcribe(_silent_pcm(0.5), language="en")
    first_language = transcriptions.received_kwargs["language"]
    stt.transcribe(_silent_pcm(0.5), language="fr")
    second_language = transcriptions.received_kwargs["language"]

    assert [first_language, second_language] == ["en", "fr"]


def test_uploads_the_audio_wrapped_in_a_wav_container():
    stt, transcriptions = _make_stt()

    stt.transcribe(_silent_pcm(0.5), language="en")

    wav_bytes = _uploaded_file_bytes(transcriptions)
    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"


def test_uploaded_wav_carries_every_pcm_sample_at_the_pipeline_audio_format():
    pcm = _silent_pcm(0.25)
    stt, transcriptions = _make_stt()

    stt.transcribe(pcm, language="en")

    assert_wav_carries_pcm_at_pipeline_format(_uploaded_file_bytes(transcriptions), pcm)


def test_rejects_pcm_with_odd_byte_length():
    stt, _ = _make_stt()

    with pytest.raises(ValueError):
        stt.transcribe(b"\x00\x00\x00", language="en")
