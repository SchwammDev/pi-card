from abc import ABC, abstractmethod


class AudioOutput(ABC):
    """Sink for mono 16-bit PCM at 16 kHz."""

    @abstractmethod
    def play(self, pcm: bytes) -> None:
        """Play a buffer of PCM audio and block until playback finishes."""
