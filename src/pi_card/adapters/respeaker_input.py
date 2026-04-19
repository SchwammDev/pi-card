from pi_card.hardware.audio_input import (
    AudioInput,
    AudioInputExhausted,
    CHANNELS,
    FRAME_SAMPLES,
    SAMPLE_RATE_HZ,
)


class ReSpeakerInput(AudioInput):
    """AudioInput backed by the ReSpeaker 4-Mic HAT via ALSA/portaudio.

    Uses sounddevice to open a blocking 16 kHz mono 16-bit PCM stream and
    yields `FRAME_SAMPLES`-sample frames, matching the project's audio contract."""

    def __init__(self, *, device: str | int | None = None):
        import sounddevice as sd  # type: ignore[import-not-found]

        self._stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE_HZ,
            blocksize=FRAME_SAMPLES,
            channels=CHANNELS,
            dtype="int16",
            device=device,
        )
        self._stream.start()

    def read_frame(self) -> bytes:
        data, overflowed = self._stream.read(FRAME_SAMPLES)
        if overflowed:
            # Overflow means the kernel buffer filled before we read it.
            # Surface it rather than silently corrupting the audio timeline.
            raise AudioInputExhausted("audio input overflowed")
        return bytes(data)

    def close(self) -> None:
        self._stream.stop()
        self._stream.close()
