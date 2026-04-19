import numpy as np

from pi_card.hardware.audio_input import SAMPLE_RATE_HZ

ERROR_TONE_DURATION_MS = 220
_ERROR_TONE_FREQUENCY_HZ = 440
_ERROR_TONE_PEAK_AMPLITUDE = 10_000
_FADE_MS = 20


def error_tone() -> bytes:
    """Short 440 Hz sine at 16 kHz mono 16-bit PCM, with linear fades to avoid clicks."""
    n = SAMPLE_RATE_HZ * ERROR_TONE_DURATION_MS // 1000
    t = np.arange(n) / SAMPLE_RATE_HZ
    signal = np.sin(2 * np.pi * _ERROR_TONE_FREQUENCY_HZ * t)

    fade = SAMPLE_RATE_HZ * _FADE_MS // 1000
    envelope = np.ones(n)
    envelope[:fade] = np.linspace(0.0, 1.0, fade)
    envelope[-fade:] = np.linspace(1.0, 0.0, fade)

    return (signal * envelope * _ERROR_TONE_PEAK_AMPLITUDE).astype(np.int16).tobytes()
