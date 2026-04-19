from pi_card.hardware.audio_output import AudioOutput

SAMPLE_RATE_HZ = 16_000
CHANNELS = 1


class USBSpeakerOutput(AudioOutput):
    """AudioOutput that plays 16 kHz mono 16-bit PCM through a USB speaker
    via ALSA/portaudio. Blocks until the buffer has drained."""

    def __init__(self, *, device: str | int | None = None):
        import numpy as np  # noqa: F401  (used in play)
        import sounddevice as sd  # type: ignore[import-not-found]

        self._sd = sd
        self._device = device

    def play(self, pcm: bytes) -> None:
        if not pcm:
            return

        import numpy as np

        samples = np.frombuffer(pcm, dtype=np.int16)
        self._sd.play(
            samples,
            samplerate=SAMPLE_RATE_HZ,
            device=self._device,
            blocking=True,
        )
