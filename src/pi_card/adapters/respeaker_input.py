import sys

from pi_card.hardware.audio_input import (
    AudioInput,
    FRAME_SAMPLES,
    SAMPLE_RATE_HZ,
)

DEFAULT_DEVICE = "ac108"
NATIVE_CHANNELS = 4
DEFAULT_MIC_CHANNEL = 0


class ReSpeakerInput(AudioInput):
    """AudioInput backed by the ReSpeaker 4-Mic HAT via the AC108 ALSA device.

    The HAT's AC108 codec only accepts 4-channel S32_LE capture — asking
    ALSA to convert to S16_LE/mono via `plughw` wedges the driver. We open
    the stream in its native format and downmix here: pick one mic channel
    and take the top 16 bits of each 32-bit sample to land in int16 range."""

    def __init__(
        self,
        *,
        device: str | int | None = DEFAULT_DEVICE,
        channel: int = DEFAULT_MIC_CHANNEL,
    ):
        import sounddevice as sd  # type: ignore[import-not-found]

        self._channel = channel
        self._stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE_HZ,
            blocksize=FRAME_SAMPLES,
            channels=NATIVE_CHANNELS,
            dtype="int32",
            device=device,
        )
        try:
            self._stream.start()
        except Exception:
            self._stream.close()
            raise

    def read_frame(self) -> bytes:
        import numpy as np

        data, overflowed = self._stream.read(FRAME_SAMPLES)
        if overflowed:
            print("audio input overflowed", file=sys.stderr)
        frame = np.frombuffer(bytes(data), dtype=np.int32).reshape(-1, NATIVE_CHANNELS)
        mono = (frame[:, self._channel] >> 16).astype(np.int16)
        return mono.tobytes()

    def close(self) -> None:
        self._stream.stop()
        self._stream.close()

    def __enter__(self) -> "ReSpeakerInput":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()
