import wave

import pytest

from pi_card.pipeline.tts import PiperTTS
from tests.fakes.audio_output import FakeAudioOutput
from tests.fakes.piper_voice import FakePiperVoice


TARGET_SAMPLE_RATE = 16_000


def _sine_pcm(seconds: float, sample_rate: int, frequency: float = 440.0) -> bytes:
    import math

    n = int(seconds * sample_rate)
    peak = 10_000
    samples = bytearray()
    for i in range(n):
        value = int(peak * math.sin(2 * math.pi * frequency * i / sample_rate))
        samples += value.to_bytes(2, byteorder="little", signed=True)
    return bytes(samples)


def test_synthesizes_the_requested_text():
    voice = FakePiperVoice()
    tts = PiperTTS(voice=voice)

    tts.speak("Hello there", FakeAudioOutput())

    assert voice.synthesized == ["Hello there"]


def test_plays_synthesized_audio_through_the_sink():
    voice = FakePiperVoice(pcm=b"\x11\x22" * 50, sample_rate=TARGET_SAMPLE_RATE)
    sink = FakeAudioOutput()
    tts = PiperTTS(voice=voice)

    tts.speak("hi", sink)

    assert sink.played == [b"\x11\x22" * 50]


def test_passes_through_audio_already_at_target_sample_rate():
    pcm = _sine_pcm(0.1, TARGET_SAMPLE_RATE)
    voice = FakePiperVoice(pcm=pcm, sample_rate=TARGET_SAMPLE_RATE)
    sink = FakeAudioOutput()

    PiperTTS(voice=voice).speak("hi", sink)

    assert sink.played == [pcm]


def test_resamples_voice_output_to_sixteen_kilohertz(tmp_path):
    source_rate = 22_050
    pcm_source = _sine_pcm(0.5, source_rate)
    voice = FakePiperVoice(pcm=pcm_source, sample_rate=source_rate)
    sink = FakeAudioOutput()

    PiperTTS(voice=voice).speak("hi", sink)

    assert len(sink.played) == 1
    out = sink.played[0]
    expected_samples = int(round(0.5 * TARGET_SAMPLE_RATE))
    assert len(out) == expected_samples * 2


def test_produces_playable_sixteen_kilohertz_mono_pcm(tmp_path):
    pcm = _sine_pcm(0.2, TARGET_SAMPLE_RATE)
    voice = FakePiperVoice(pcm=pcm, sample_rate=TARGET_SAMPLE_RATE)
    sink = FakeAudioOutput()

    PiperTTS(voice=voice).speak("hi", sink)

    out_path = tmp_path / "out.wav"
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TARGET_SAMPLE_RATE)
        w.writeframes(b"".join(sink.played))

    with wave.open(str(out_path), "rb") as r:
        assert r.getframerate() == TARGET_SAMPLE_RATE
        assert r.getnchannels() == 1
        assert r.getsampwidth() == 2
        assert r.getnframes() > 0


def test_rejects_empty_text():
    tts = PiperTTS(voice=FakePiperVoice())

    with pytest.raises(ValueError):
        tts.speak("", FakeAudioOutput())
