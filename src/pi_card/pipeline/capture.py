from dataclasses import dataclass

import numpy as np

from pi_card.hardware.audio_input import AudioInput, FRAME_DURATION_MS

DEFAULT_SILENCE_MS_AFTER_SPEECH = 500
DEFAULT_SILENCE_MS_NO_SPEECH = 5_000
DEFAULT_MAX_MS = 20_000
DEFAULT_START_SPEECH_FRAMES = 2

_SPEECH_RMS_THRESHOLD = 1500


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
    start_speech_frames: int = DEFAULT_START_SPEECH_FRAMES,
) -> Utterance | SilenceTimeout:
    """Read frames from `audio_in` until one of three conditions fires:

    - no speech heard for `silence_ms_no_speech` ms → SilenceTimeout
    - speech heard, then `silence_ms_after_speech` ms of trailing silence → Utterance
    - buffered speech reaches `max_ms` → Utterance (truncated)

    Capture only starts after `start_speech_frames` consecutive frames cross
    the RMS threshold; this debounces single noise spikes that would otherwise
    seed Whisper with garbage."""
    trailing_silence_limit = _ms_to_frames(silence_ms_after_speech)
    no_speech_limit = _ms_to_frames(silence_ms_no_speech)
    max_frames = _ms_to_frames(max_ms)

    captured: list[bytes] = []
    speech_streak: list[bytes] = []
    leading_silence = 0
    trailing_silence = 0

    while True:
        frame = audio_in.read_frame()
        is_speech = _is_speech(frame)

        if not captured:
            if is_speech:
                speech_streak.append(frame)
                if len(speech_streak) >= start_speech_frames:
                    captured.extend(speech_streak)
                    speech_streak.clear()
                    if len(captured) >= max_frames:
                        return Utterance(pcm=b"".join(captured))
            else:
                speech_streak.clear()
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
