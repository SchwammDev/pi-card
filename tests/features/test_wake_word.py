import pytest

from pi_card.hardware.audio_input import FRAME_BYTES
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

    with pytest.raises(RuntimeError):
        detector.wait_for_wake_word(audio)


def test_matches_configured_wake_word_name():
    engine = FakeWakeWordEngine(model_name="jarvis", scores=[0.9])
    audio = FakeAudioInput(frames=[SILENCE_FRAME])
    detector = WakeWordDetector(
        engine=engine, model_name="jarvis", threshold=0.5
    )

    detector.wait_for_wake_word(audio)


def test_ignores_scores_for_other_wake_words():
    class NoisyEngine:
        def __init__(self):
            self.call = 0

        def predict(self, frame):
            self.call += 1
            if self.call == 1:
                return {"alexa": 0.99, "computer": 0.1}
            return {"alexa": 0.2, "computer": 0.9}

    audio = FakeAudioInput(frames=[SILENCE_FRAME, SILENCE_FRAME, SILENCE_FRAME])
    engine = NoisyEngine()
    detector = WakeWordDetector(
        engine=engine, model_name="computer", threshold=0.5
    )

    detector.wait_for_wake_word(audio)

    assert engine.call == 2
