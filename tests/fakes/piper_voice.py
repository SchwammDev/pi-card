from typing import Callable


class FakePiperVoice:
    def __init__(
        self,
        pcm: bytes = b"\x00\x00" * 100,
        sample_rate: int = 16_000,
        snapshot_provider: Callable[[], int] | None = None,
    ):
        self._pcm = pcm
        self.sample_rate = sample_rate
        self.synthesized: list[str] = []
        self._snapshot_provider = snapshot_provider
        self.deltas_yielded_at_first_synthesize: list[int] = []

    def set_pcm(self, pcm: bytes, sample_rate: int) -> None:
        self._pcm = pcm
        self.sample_rate = sample_rate

    def attach_stream_observer(self, snapshot_provider: Callable[[], int]) -> None:
        self._snapshot_provider = snapshot_provider

    def synthesize(self, text: str) -> bytes:
        if not self.synthesized and self._snapshot_provider is not None:
            self.deltas_yielded_at_first_synthesize.append(self._snapshot_provider())
        self.synthesized.append(text)
        return self._pcm
