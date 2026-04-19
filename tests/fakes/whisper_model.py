from dataclasses import dataclass


@dataclass
class _Segment:
    text: str


class FakeWhisperModel:
    """Imitates faster-whisper's transcribe signature with per-language canned text."""

    def __init__(self, transcripts_by_language: dict[str, str] | None = None):
        self._transcripts = dict(transcripts_by_language or {})
        self.calls: list[dict] = []

    def set_transcript(self, language: str, text: str) -> None:
        self._transcripts[language] = text

    def transcribe(self, audio, language: str, **kwargs):
        self.calls.append(
            {
                "language": language,
                "num_samples": len(audio),
                "kwargs": kwargs,
            }
        )
        text = self._transcripts.get(language, "")
        return iter([_Segment(text=text)]), None
