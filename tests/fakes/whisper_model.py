from collections import defaultdict, deque
from dataclasses import dataclass


CONFIDENT_AVG_LOGPROB = -0.3


@dataclass
class _Segment:
    text: str
    avg_logprob: float = CONFIDENT_AVG_LOGPROB


class FakeWhisperModel:
    """Imitates faster-whisper's transcribe signature. Supports both fixed
    per-language transcripts and a FIFO queue for sequenced calls."""

    def __init__(self, transcripts_by_language: dict[str, str] | None = None):
        self._transcripts: dict[str, str] = dict(transcripts_by_language or {})
        self._queued: dict[str, deque[tuple[str, float]]] = defaultdict(deque)
        self.calls: list[dict] = []

    def set_transcript(self, language: str, text: str) -> None:
        self._transcripts[language] = text

    def queue_transcript(
        self, language: str, text: str, *, avg_logprob: float = CONFIDENT_AVG_LOGPROB
    ) -> None:
        self._queued[language].append((text, avg_logprob))

    def transcribe(self, audio, language: str, **kwargs):
        self.calls.append(
            {
                "language": language,
                "num_samples": len(audio),
                "kwargs": kwargs,
            }
        )
        if self._queued[language]:
            text, avg_logprob = self._queued[language].popleft()
        else:
            text = self._transcripts.get(language, "")
            avg_logprob = CONFIDENT_AVG_LOGPROB
        return iter([_Segment(text=text, avg_logprob=avg_logprob)]), None
