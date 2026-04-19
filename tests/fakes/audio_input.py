from collections.abc import Iterator

from pi_card.hardware.audio_input import AudioInput, FRAME_BYTES


class FakeAudioInput(AudioInput):
    """Yields pre-loaded PCM frames. Silence fills any frame-sized gap."""

    def __init__(self, frames: list[bytes] | None = None):
        self._frames: list[bytes] = list(frames) if frames else []

    def queue(self, pcm: bytes) -> None:
        """Append raw PCM, split into FRAME_BYTES chunks with trailing silence padding."""
        for start in range(0, len(pcm), FRAME_BYTES):
            chunk = pcm[start : start + FRAME_BYTES]
            if len(chunk) < FRAME_BYTES:
                chunk = chunk + b"\x00" * (FRAME_BYTES - len(chunk))
            self._frames.append(chunk)

    def frames(self) -> Iterator[bytes]:
        yield from self._frames
