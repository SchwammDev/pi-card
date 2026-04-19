from pi_card.hardware.audio_output import AudioOutput


class FakeAudioOutput(AudioOutput):
    """Records every played buffer so tests can assert on what was spoken."""

    def __init__(self):
        self.played: list[bytes] = []

    def play(self, pcm: bytes) -> None:
        self.played.append(pcm)
