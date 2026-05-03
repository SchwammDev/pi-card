import pytest

from pi_card.hardware.audio_input import (
    AudioInputExhausted,
    FRAME_BYTES,
    FRAME_DURATION_MS,
)
from pi_card.pipeline.capture import SilenceTimeout, Utterance, capture_utterance
from tests.fakes.audio_input import FakeAudioInput
from tests.fakes.speech_detector import ScriptedSpeechDetector


SPEECH_FRAME = b"\x01\x00" * (FRAME_BYTES // 2)
SILENCE_FRAME = b"\x00\x00" * (FRAME_BYTES // 2)

_FRAME_SYMBOLS = {"S": SILENCE_FRAME, "V": SPEECH_FRAME}


def _audio_and_detector(pattern: str) -> tuple[FakeAudioInput, ScriptedSpeechDetector]:
    frames = [_FRAME_SYMBOLS[c] for c in pattern]
    is_speech = [c == "V" for c in pattern]
    return FakeAudioInput(frames=frames), ScriptedSpeechDetector(is_speech)


def _pcm(pattern: str) -> bytes:
    return b"".join(_FRAME_SYMBOLS[c] for c in pattern)


def test_returns_silence_timeout_when_only_silence_is_heard():
    audio, detector = _audio_and_detector("SSS")

    result = capture_utterance(audio, detector, silence_ms_no_speech=2 * FRAME_DURATION_MS)

    assert isinstance(result, SilenceTimeout)


def test_returns_utterance_when_speech_is_followed_by_trailing_silence():
    audio, detector = _audio_and_detector("VVSS")

    result = _capture(audio, detector)

    assert isinstance(result, Utterance)
    assert result.pcm == _pcm("VVSS")


def test_capture_includes_preroll_frames_to_recover_quiet_leading_speech():
    audio, detector = _audio_and_detector("SSVVSS")

    result = _capture(audio, detector, preroll_frames=4)

    assert isinstance(result, Utterance)
    assert result.pcm == _pcm("SSVVSS")


def test_preroll_buffer_keeps_only_the_last_n_frames_before_speech():
    audio, detector = _audio_and_detector("SSSSSSVVSS")

    result = _capture(audio, detector, preroll_frames=3)

    assert isinstance(result, Utterance)
    assert result.pcm == _pcm("SVVSS")


def test_isolated_noise_spike_does_not_start_capture():
    audio, detector = _audio_and_detector("SVSSS")

    result = capture_utterance(
        audio, detector, silence_ms_no_speech=4 * FRAME_DURATION_MS,
    )

    assert isinstance(result, SilenceTimeout)


def test_capture_commits_only_after_consecutive_speech_frames():
    audio, detector = _audio_and_detector("SVSVVSS")

    result = _capture(audio, detector, preroll_frames=2)

    assert isinstance(result, Utterance)
    assert result.pcm == _pcm("VVSS")


def test_truncates_at_max_ms_when_speech_continues():
    result = _capture_with_max_frames("V" * 10, max_frames=2)

    assert isinstance(result, Utterance)
    assert len(result.pcm) == 2 * FRAME_BYTES


def _capture_with_max_frames(pattern: str, *, max_frames: int):
    audio, detector = _audio_and_detector(pattern)
    return capture_utterance(
        audio, detector,
        silence_ms_after_speech=100 * FRAME_DURATION_MS,
        silence_ms_no_speech=100 * FRAME_DURATION_MS,
        max_ms=max_frames * FRAME_DURATION_MS,
    )


def test_natural_one_second_pause_inside_speech_does_not_end_the_turn():
    audio, detector = _audio_and_detector("VV" + "S" * 13 + "VV" + "S" * 20)

    result = capture_utterance(audio, detector)

    assert isinstance(result, Utterance)
    assert result.pcm.count(SPEECH_FRAME) == 4


def test_detector_is_reset_at_the_start_of_capture():
    audio, detector = _audio_and_detector("SSS")

    capture_utterance(audio, detector, silence_ms_no_speech=2 * FRAME_DURATION_MS)

    assert detector.reset_call_count == 1


def test_propagates_audio_input_exhausted_if_stream_runs_out_mid_capture():
    audio, detector = _audio_and_detector("V")

    with pytest.raises(AudioInputExhausted):
        _capture(audio, detector)


def _capture(audio, detector, *, preroll_frames=24):
    return capture_utterance(
        audio, detector,
        silence_ms_after_speech=2 * FRAME_DURATION_MS,
        silence_ms_no_speech=100 * FRAME_DURATION_MS,
        preroll_frames=preroll_frames,
    )
