import pytest

from pi_card.hardware.audio_input import (
    AudioInputExhausted,
    FRAME_BYTES,
    FRAME_DURATION_MS,
)
from pi_card.pipeline.capture import SilenceTimeout, Utterance, capture_utterance
from tests.fakes.audio_input import FakeAudioInput

SILENCE_FRAME = b"\x00" * FRAME_BYTES
SPEECH_FRAME = b"\x00\x20" * (FRAME_BYTES // 2)  # amplitude 8192 samples — well above the noise-floor threshold

_FRAME_SYMBOLS = {"S": SILENCE_FRAME, "V": SPEECH_FRAME}


def _audio(pattern: str) -> FakeAudioInput:
    return FakeAudioInput(frames=[_FRAME_SYMBOLS[c] for c in pattern])


def _pcm(pattern: str) -> bytes:
    return b"".join(_FRAME_SYMBOLS[c] for c in pattern)


def test_returns_silence_timeout_when_only_silence_is_heard():
    audio = FakeAudioInput(frames=[SILENCE_FRAME, SILENCE_FRAME, SILENCE_FRAME])

    result = capture_utterance(audio, silence_ms_no_speech=2 * FRAME_DURATION_MS)

    assert isinstance(result, SilenceTimeout)


def test_returns_utterance_when_speech_is_followed_by_trailing_silence():
    audio = FakeAudioInput(
        frames=[SPEECH_FRAME, SPEECH_FRAME, SILENCE_FRAME, SILENCE_FRAME]
    )

    result = capture_utterance(
        audio,
        silence_ms_after_speech=2 * FRAME_DURATION_MS,
        silence_ms_no_speech=100 * FRAME_DURATION_MS,
    )

    assert isinstance(result, Utterance)
    assert result.pcm == SPEECH_FRAME * 2 + SILENCE_FRAME * 2


def test_capture_includes_preroll_frames_to_recover_quiet_leading_speech():
    result = _capture(_audio("SSVVSS"), preroll_frames=4)

    assert isinstance(result, Utterance)
    assert result.pcm == _pcm("SSVVSS")


def test_preroll_buffer_keeps_only_the_last_n_frames_before_speech():
    result = _capture(_audio("SSSSSSVVSS"), preroll_frames=3)

    assert isinstance(result, Utterance)
    assert result.pcm == _pcm("SVVSS")


def _capture(audio, *, preroll_frames):
    return capture_utterance(
        audio,
        silence_ms_after_speech=2 * FRAME_DURATION_MS,
        silence_ms_no_speech=100 * FRAME_DURATION_MS,
        preroll_frames=preroll_frames,
    )


def test_isolated_noise_spike_does_not_start_capture():
    audio = FakeAudioInput(
        frames=[SILENCE_FRAME, SPEECH_FRAME, SILENCE_FRAME, SILENCE_FRAME, SILENCE_FRAME]
    )

    result = capture_utterance(
        audio,
        silence_ms_no_speech=4 * FRAME_DURATION_MS,
    )

    assert isinstance(result, SilenceTimeout)


def test_capture_commits_only_after_consecutive_speech_frames():
    result = _capture(_audio("SVSVVSS"), preroll_frames=2)

    assert isinstance(result, Utterance)
    assert result.pcm == _pcm("VVSS")


def test_truncates_at_max_ms_when_speech_continues():
    audio = FakeAudioInput(frames=[SPEECH_FRAME] * 10)

    result = capture_utterance(
        audio,
        silence_ms_after_speech=100 * FRAME_DURATION_MS,
        silence_ms_no_speech=100 * FRAME_DURATION_MS,
        max_ms=2 * FRAME_DURATION_MS,
    )

    assert isinstance(result, Utterance)
    assert len(result.pcm) == 2 * FRAME_BYTES


def test_propagates_audio_input_exhausted_if_stream_runs_out_mid_capture():
    audio = FakeAudioInput(frames=[SPEECH_FRAME])

    with pytest.raises(AudioInputExhausted):
        capture_utterance(
            audio,
            silence_ms_after_speech=2 * FRAME_DURATION_MS,
            silence_ms_no_speech=100 * FRAME_DURATION_MS,
        )
