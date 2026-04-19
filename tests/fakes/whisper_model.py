from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class _Segment:
    text: str


class FakeWhisperModel:
    """Imitates faster-whisper's transcribe signature. Supports both fixed
    per-language transcripts and a FIFO queue for sequenced calls."""

    def __init__(self, transcripts_by_language: dict[str, str] | None = None):
        self._transcripts: dict[str, str] = dict(transcripts_by_language or {})
        self._queued: dict[str, deque[str]] = defaultdict(deque)
        self.calls: list[dict] = []

    def set_transcript(self, language: str, text: str) -> None:
        self._transcripts[language] = text

    def queue_transcript(self, language: str, text: str) -> None:
        self._queued[language].append(text)

    def transcribe(self, audio, language: str, **kwargs):
        self.calls.append(
            {
                "language": language,
                "num_samples": len(audio),
                "kwargs": kwargs,
            }
        )
        if self._queued[language]:
            text = self._queued[language].popleft()
        else:
            text = self._transcripts.get(language, "")
        return iter([_Segment(text=text)]), None
