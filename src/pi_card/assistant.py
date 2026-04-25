from pi_card.conversation import Conversation
from pi_card.hardware.ai_agent import AIAgent
from pi_card.hardware.audio_input import AudioInput
from pi_card.hardware.audio_output import AudioOutput
from pi_card.hardware.leds import LEDController, LEDState
from pi_card.pipeline.stt import WhisperSTT
from pi_card.pipeline.tts import PiperTTS
from pi_card.pipeline.wake_word import WakeWordDetector


class VoiceAssistant:
    """Top-level orchestrator. Loops wake-word → conversation → wake-word."""

    def __init__(
        self,
        *,
        audio_in: AudioInput,
        audio_out: AudioOutput,
        leds: LEDController,
        agent: AIAgent,
        wake_word_detector: WakeWordDetector,
        stt: WhisperSTT,
        tts_by_language: dict[str, PiperTTS],
        language: str = "en",
        silence_timeout: float = 5.0,
        max_stt_retries: int = 2,
    ):
        self.audio_in = audio_in
        self.audio_out = audio_out
        self.leds = leds
        self.agent = agent
        self.wake_word_detector = wake_word_detector
        self.stt = stt
        self.tts_by_language = tts_by_language
        self.language = language
        self.silence_timeout = silence_timeout
        self.max_stt_retries = max_stt_retries

    def run(self) -> None:
        while True:
            self.leds.set_state(LEDState.OFF)
            self.wake_word_detector.wait_for_wake_word(self.audio_in)
            self.language = self._new_conversation().run()

    def _new_conversation(self) -> Conversation:
        return Conversation(
            audio_in=self.audio_in,
            audio_out=self.audio_out,
            leds=self.leds,
            agent=self.agent,
            stt=self.stt,
            tts_by_language=self.tts_by_language,
            initial_language=self.language,
            silence_timeout_ms=int(self.silence_timeout * 1000),
            max_stt_retries=self.max_stt_retries,
        )
