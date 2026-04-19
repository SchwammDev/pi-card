from dataclasses import dataclass

import numpy as np

from pi_card.hardware.audio_input import AudioInput, FRAME_DURATION_MS

DEFAULT_SILENCE_MS_AFTER_SPEECH = 500
DEFAULT_SILENCE_MS_NO_SPEECH = 8_000
DEFAULT_MAX_MS = 20_000

_SPEECH_RMS_THRESHOLD = 150


@dataclass(frozen=True)
class Utterance:
    pcm: bytes


@dataclass(frozen=True)
class SilenceTimeout:
    pass


def capture_utterance(
    audio_in: AudioInput,
    *,
    silence_ms_after_speech: int = DEFAULT_SILENCE_MS_AFTER_SPEECH,
    silence_ms_no_speech: int = DEFAULT_SILENCE_MS_NO_SPEECH,
    max_ms: int = DEFAULT_MAX_MS,
) -> Utterance | SilenceTimeout:
    """Read frames from `audio_in` until one of three conditions fires:

    - no speech heard for `silence_ms_no_speech` ms → SilenceTimeout
    - speech heard, then `silence_ms_after_speech` ms of trailing silence → Utterance
    - buffered speech reaches `max_ms` → Utterance (truncated)
    """
    trailing_silence_limit = _ms_to_frames(silence_ms_after_speech)
    no_speech_limit = _ms_to_frames(silence_ms_no_speech)
    max_frames = _ms_to_frames(max_ms)

    captured: list[bytes] = []
    leading_silence = 0
    trailing_silence = 0

    while True:
        frame = audio_in.read_frame()
        is_speech = _is_speech(frame)

        if not captured:
            if is_speech:
                captured.append(frame)
            else:
                leading_silence += 1
                if leading_silence >= no_speech_limit:
                    return SilenceTimeout()
            continue

        captured.append(frame)
        trailing_silence = 0 if is_speech else trailing_silence + 1
        if trailing_silence >= trailing_silence_limit or len(captured) >= max_frames:
            return Utterance(pcm=b"".join(captured))


def _ms_to_frames(ms: int) -> int:
    return max(1, ms // FRAME_DURATION_MS)


def _is_speech(frame: bytes) -> bool:
    samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
    if samples.size == 0:
        return False
    rms = float(np.sqrt(np.mean(samples**2)))
    return rms >= _SPEECH_RMS_THRESHOLD
