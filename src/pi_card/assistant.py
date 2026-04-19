from pi_card.hardware.ai_agent import AIAgent
from pi_card.hardware.audio_input import AudioInput
from pi_card.hardware.audio_output import AudioOutput
from pi_card.hardware.leds import LEDController


class VoiceAssistant:
    """Top-level orchestrator. Phase 1: wiring only, no behavior."""

    def __init__(
        self,
        *,
        audio_in: AudioInput,
        audio_out: AudioOutput,
        leds: LEDController,
        agent: AIAgent,
    ):
        self.audio_in = audio_in
        self.audio_out = audio_out
        self.leds = leds
        self.agent = agent
