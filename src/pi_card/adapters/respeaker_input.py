import subprocess

from pi_card.hardware.audio_input import (
    AudioInput,
    AudioInputExhausted,
    FRAME_SAMPLES,
    SAMPLE_RATE_HZ,
)

DEFAULT_DEVICE = "ac108"
NATIVE_CHANNELS = 4
NATIVE_SAMPLE_BYTES = 4  # S32_LE
DEFAULT_MIC_CHANNEL = 0


class ReSpeakerInput(AudioInput):
    """AudioInput backed by the ReSpeaker 4-Mic HAT via an `arecord` subprocess.

    sounddevice/PortAudio's open path on the AC108 wedges on Pi 5 — almost any
    kernel I/O activity in the parent process before the open hangs the driver.
    Driving `arecord` as a child process sidesteps PortAudio entirely; ALSA
    itself is reliable when accessed directly.

    arecord is told to capture in the codec's native S32_LE / 4-channel format;
    we downmix in Python by picking one mic channel and taking the top 16 bits
    of each 32-bit sample to land in int16 range."""

    _frame_bytes_native = FRAME_SAMPLES * NATIVE_CHANNELS * NATIVE_SAMPLE_BYTES

    def __init__(
        self,
        *,
        device: str = DEFAULT_DEVICE,
        channel: int = DEFAULT_MIC_CHANNEL,
    ):
        self._channel = channel
        self._proc = subprocess.Popen(
            [
                "arecord",
                "-D", device,
                "-q",
                "-f", "S32_LE",
                "-r", str(SAMPLE_RATE_HZ),
                "-c", str(NATIVE_CHANNELS),
                "-t", "raw",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def read_frame(self) -> bytes:
        import numpy as np

        data = self._read_exact(self._frame_bytes_native)
        frame = np.frombuffer(data, dtype=np.int32).reshape(-1, NATIVE_CHANNELS)
        mono = (frame[:, self._channel] >> 16).astype(np.int16)
        return mono.tobytes()

    def _read_exact(self, n: int) -> bytes:
        assert self._proc.stdout is not None
        chunks: list[bytes] = []
        remaining = n
        while remaining > 0:
            chunk = self._proc.stdout.read(remaining)
            if not chunk:
                raise AudioInputExhausted("arecord stream closed")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def close(self) -> None:
        self._proc.terminate()
        try:
            self._proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait()
        if self._proc.stdout is not None:
            self._proc.stdout.close()

    def __enter__(self) -> "ReSpeakerInput":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()
