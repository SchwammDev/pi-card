import numpy as np

from pi_card.audio_tones import (
    ERROR_TONE_DURATION_MS,
    READY_TONE_DURATION_MS,
    error_tone,
    ready_tone,
)
from pi_card.hardware.audio_input import SAMPLE_RATE_HZ, SAMPLE_WIDTH_BYTES


def _samples(pcm: bytes) -> np.ndarray:
    return np.frombuffer(pcm, dtype=np.int16)


def test_error_tone_length_matches_sample_rate_times_duration():
    pcm = error_tone()
    expected_samples = SAMPLE_RATE_HZ * ERROR_TONE_DURATION_MS // 1000

    assert len(pcm) == expected_samples * SAMPLE_WIDTH_BYTES


def test_error_tone_is_not_silent():
    peak = int(np.max(np.abs(_samples(error_tone()))))

    assert peak > 1000


def test_error_tone_peak_stays_below_full_scale():
    peak = int(np.max(np.abs(_samples(error_tone()))))

    assert peak < 32_000  # headroom to avoid clipping


def test_error_tone_fades_in_and_out_to_avoid_clicks():
    samples = _samples(error_tone())

    assert abs(int(samples[0])) < 100
    assert abs(int(samples[-1])) < 100


def test_error_tone_is_deterministic():
    assert error_tone() == error_tone()


def test_ready_tone_length_matches_sample_rate_times_duration():
    expected_samples = SAMPLE_RATE_HZ * READY_TONE_DURATION_MS // 1000

    assert len(ready_tone()) == expected_samples * SAMPLE_WIDTH_BYTES


def test_ready_tone_is_not_silent():
    peak = int(np.max(np.abs(_samples(ready_tone()))))

    assert peak > 1000


def test_ready_tone_fades_in_and_out_to_avoid_clicks():
    samples = _samples(ready_tone())

    assert abs(int(samples[0])) < 100
    assert abs(int(samples[-1])) < 100


def test_ready_tone_rises_in_pitch_so_it_sounds_distinct_from_error():
    samples = _samples(ready_tone())
    half = len(samples) // 2

    first_half_zero_crossings = np.sum(np.diff(np.sign(samples[:half])) != 0)
    second_half_zero_crossings = np.sum(np.diff(np.sign(samples[half:])) != 0)

    assert second_half_zero_crossings > first_half_zero_crossings
