import pytest

from pi_card.hardware.audio_input import AudioInputExhausted, FRAME_BYTES
from pi_card.pipeline.wake_word import WakeWordDetector
from tests.fakes.audio_input import FakeAudioInput
from tests.fakes.wake_word_engine import FakeWakeWordEngine


SILENCE_FRAME = b"\x00" * FRAME_BYTES


def test_returns_when_engine_score_crosses_threshold():
    engine = FakeWakeWordEngine(scores=[0.1, 0.2, 0.9])
    audio = FakeAudioInput(frames=[SILENCE_FRAME] * 3)
    detector = WakeWordDetector(engine=engine, threshold=0.5)

    detector.wait_for_wake_word(audio)


def test_stops_consuming_frames_after_detection():
    engine = FakeWakeWordEngine(scores=[0.9, 0.9, 0.9])
    audio = FakeAudioInput(frames=[SILENCE_FRAME] * 5)
    detector = WakeWordDetector(engine=engine, threshold=0.5)

    detector.wait_for_wake_word(audio)

    assert len(engine.frames_seen) == 1


def test_waits_across_silence_before_detection():
    engine = FakeWakeWordEngine(scores=[0.0, 0.0, 0.0, 0.8])
    audio = FakeAudioInput(frames=[SILENCE_FRAME] * 10)
    detector = WakeWordDetector(engine=engine, threshold=0.5)

    detector.wait_for_wake_word(audio)

    assert len(engine.frames_seen) == 4


def test_feeds_frames_to_the_engine_unchanged():
    frame_a = b"\x01\x02" * (FRAME_BYTES // 2)
    frame_b = b"\x03\x04" * (FRAME_BYTES // 2)
    engine = FakeWakeWordEngine(scores=[0.0, 0.9])
    audio = FakeAudioInput(frames=[frame_a, frame_b])
    detector = WakeWordDetector(engine=engine, threshold=0.5)

    detector.wait_for_wake_word(audio)

    assert engine.frames_seen == [frame_a, frame_b]


def test_raises_when_audio_stream_ends_without_detection():
    engine = FakeWakeWordEngine(scores=[0.1, 0.2])
    audio = FakeAudioInput(frames=[SILENCE_FRAME, SILENCE_FRAME])
    detector = WakeWordDetector(engine=engine, threshold=0.5)

    with pytest.raises(AudioInputExhausted):
        detector.wait_for_wake_word(audio)


def test_matches_configured_wake_word_name():
    engine = FakeWakeWordEngine(model_name="jarvis", scores=[0.9])
    audio = FakeAudioInput(frames=[SILENCE_FRAME])
    detector = WakeWordDetector(
        engine=engine, model_name="jarvis", threshold=0.5
    )

    detector.wait_for_wake_word(audio)


class _MultiModelScriptedEngine:
    def __init__(self, *, scripted_calls: list[dict[str, float]]):
        self._scripted_calls = scripted_calls
        self.call = 0

    def predict(self, frame):
        scores = self._scripted_calls[self.call]
        self.call += 1
        return scores

    def reset(self):
        pass


def test_ignores_scores_for_other_wake_words():
    engine = _engine_that_peaks_alexa_then_computer()

    _detect(engine, target="computer")

    assert engine.call == 2


def _engine_that_peaks_alexa_then_computer():
    return _MultiModelScriptedEngine(scripted_calls=[
        {"alexa": 0.99, "computer": 0.1},
        {"alexa": 0.2, "computer": 0.9},
    ])


def _detect(engine, *, target: str):
    audio = FakeAudioInput(frames=[SILENCE_FRAME] * 3)
    WakeWordDetector(engine=engine, model_name=target, threshold=0.5).wait_for_wake_word(audio)
