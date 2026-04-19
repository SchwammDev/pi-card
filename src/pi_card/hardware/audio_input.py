from abc import ABC, abstractmethod
from collections.abc import Iterator

SAMPLE_RATE_HZ = 16_000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
FRAME_SAMPLES = 1280
FRAME_BYTES = FRAME_SAMPLES * SAMPLE_WIDTH_BYTES


class AudioInput(ABC):
    """Source of mono 16-bit PCM frames at 16 kHz, 1280 samples per frame."""

    @abstractmethod
    def frames(self) -> Iterator[bytes]:
        """Yield audio frames until the source is exhausted or stopped."""
