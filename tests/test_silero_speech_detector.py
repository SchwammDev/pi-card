import numpy as np

from pi_card.pipeline.speech_detector import (
    SILERO_WINDOW_SAMPLES,
    SileroSpeechDetector,
)
from tests.fakes.speech_detector import FakeSileroBackend


SAMPLES_PER_INPUT_FRAME = 1280


def _frame(value: int = 1000) -> bytes:
    return np.full(SAMPLES_PER_INPUT_FRAME, value, dtype=np.int16).tobytes()


def test_one_input_frame_drives_two_inference_windows_and_holds_the_remainder():
    backend = FakeSileroBackend()
    detector = SileroSpeechDetector(backend)

    detector.is_speech(_frame())

    assert len(backend.windows_seen) == 2
    assert all(w.shape == (SILERO_WINDOW_SAMPLES,) for w in backend.windows_seen)


def test_remainder_carries_into_the_next_frame():
    backend = FakeSileroBackend()
    detector = SileroSpeechDetector(backend)

    detector.is_speech(_frame())
    detector.is_speech(_frame())

    assert len(backend.windows_seen) == 5


def test_is_speech_is_true_when_any_window_in_the_frame_crosses_threshold():
    backend = FakeSileroBackend(probabilities=[0.1, 0.7])
    detector = SileroSpeechDetector(backend, threshold=0.5)

    assert detector.is_speech(_frame()) is True


def test_is_speech_is_false_when_all_windows_in_the_frame_are_below_threshold():
    backend = FakeSileroBackend(probabilities=[0.1, 0.2])
    detector = SileroSpeechDetector(backend, threshold=0.5)

    assert detector.is_speech(_frame()) is False


def test_threshold_is_configurable():
    assert _hears_speech_with_threshold(0.3, probabilities=[0.4, 0.4]) is True
    assert _hears_speech_with_threshold(0.8, probabilities=[0.4, 0.4]) is False


def _hears_speech_with_threshold(threshold: float, *, probabilities: list[float]) -> bool:
    detector = SileroSpeechDetector(FakeSileroBackend(probabilities), threshold=threshold)
    return detector.is_speech(_frame())


def test_samples_passed_to_backend_are_normalised_to_unit_range():
    backend = FakeSileroBackend()
    detector = SileroSpeechDetector(backend)

    detector.is_speech(_frame(value=16384))

    window = backend.windows_seen[0]
    assert window.dtype == np.float32
    assert np.allclose(window, 16384 / 32768.0)


def test_reset_clears_held_remainder_and_resets_backend():
    backend = FakeSileroBackend()
    detector = SileroSpeechDetector(backend)

    _feed_frame_then_reset_then_feed_frame(detector)

    assert _windows_seen_after_reset(backend) == 2
    assert backend.reset_call_count == 1


def _feed_frame_then_reset_then_feed_frame(detector: SileroSpeechDetector) -> None:
    detector.is_speech(_frame())
    detector.reset()
    detector.is_speech(_frame())


def _windows_seen_after_reset(backend: FakeSileroBackend) -> int:
    return len(backend.windows_seen) - 2
