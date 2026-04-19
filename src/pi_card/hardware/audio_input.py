from abc import ABC, abstractmethod

SAMPLE_RATE_HZ = 16_000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
FRAME_SAMPLES = 1280
FRAME_BYTES = FRAME_SAMPLES * SAMPLE_WIDTH_BYTES
FRAME_DURATION_MS = 1000 * FRAME_SAMPLES // SAMPLE_RATE_HZ


class AudioInputExhausted(Exception):
    """Raised when the audio stream has no more frames to read."""


class AudioInput(ABC):
    """Source of mono 16-bit PCM frames at 16 kHz, 1280 samples per frame.

    Frames are consumed once. Each call to `read_frame` returns the next
    frame and advances the stream; there is no rewind.
    """

    @abstractmethod
    def read_frame(self) -> bytes:
        """Return the next audio frame. Raise AudioInputExhausted when the stream ends."""
