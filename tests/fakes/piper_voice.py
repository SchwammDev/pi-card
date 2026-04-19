class FakePiperVoice:
    """Produces scripted PCM at a configurable sample rate."""

    def __init__(self, pcm: bytes = b"\x00\x00" * 100, sample_rate: int = 16_000):
        self._pcm = pcm
        self.sample_rate = sample_rate
        self.synthesized: list[str] = []

    def set_pcm(self, pcm: bytes, sample_rate: int) -> None:
        self._pcm = pcm
        self.sample_rate = sample_rate

    def synthesize(self, text: str) -> bytes:
        self.synthesized.append(text)
        return self._pcm
