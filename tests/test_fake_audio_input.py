import pytest

from pi_card.hardware.audio_input import AudioInputExhausted, FRAME_BYTES
from tests.fakes.audio_input import FakeAudioInput


def test_read_frame_returns_queued_frames_in_order():
    frame_a = b"\x01" * FRAME_BYTES
    frame_b = b"\x02" * FRAME_BYTES
    audio = FakeAudioInput(frames=[frame_a, frame_b])

    assert audio.read_frame() == frame_a
    assert audio.read_frame() == frame_b


def test_read_frame_raises_when_the_stream_is_exhausted():
    audio = FakeAudioInput(frames=[b"\x00" * FRAME_BYTES])
    audio.read_frame()

    with pytest.raises(AudioInputExhausted):
        audio.read_frame()


def test_read_frame_consumes_frames_so_the_stream_does_not_replay():
    audio = FakeAudioInput(frames=[b"\x01" * FRAME_BYTES])
    audio.read_frame()

    with pytest.raises(AudioInputExhausted):
        audio.read_frame()


def test_queue_splits_raw_pcm_into_frame_sized_chunks():
    audio = FakeAudioInput()
    audio.queue(b"\x01" * FRAME_BYTES * 2)

    assert audio.read_frame() == b"\x01" * FRAME_BYTES
    assert audio.read_frame() == b"\x01" * FRAME_BYTES
    with pytest.raises(AudioInputExhausted):
        audio.read_frame()
