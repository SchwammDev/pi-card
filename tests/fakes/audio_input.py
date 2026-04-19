from collections import deque

from pi_card.hardware.audio_input import (
    AudioInput,
    AudioInputExhausted,
    FRAME_BYTES,
)


class FakeAudioInput(AudioInput):
    """Stateful frame source backed by a deque. Each frame is returned once."""

    def __init__(self, frames: list[bytes] | None = None):
        self._frames: deque[bytes] = deque(frames or [])

    def queue(self, pcm: bytes) -> None:
        """Append raw PCM, split into FRAME_BYTES chunks with trailing silence padding."""
        for start in range(0, len(pcm), FRAME_BYTES):
            chunk = pcm[start : start + FRAME_BYTES]
            if len(chunk) < FRAME_BYTES:
                chunk = chunk + b"\x00" * (FRAME_BYTES - len(chunk))
            self._frames.append(chunk)

    def read_frame(self) -> bytes:
        if not self._frames:
            raise AudioInputExhausted
        return self._frames.popleft()
