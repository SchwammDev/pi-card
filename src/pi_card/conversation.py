import logging

from pi_card.audio_tones import error_tone
from pi_card.hardware.ai_agent import AIAgent, Message
from pi_card.hardware.audio_input import AudioInput
from pi_card.hardware.audio_output import AudioOutput
from pi_card.hardware.leds import LEDController, LEDState
from pi_card.messages import (
    detect_language_switch,
    is_exit_phrase,
    network_error_cue,
    repeat_prompt,
    switch_acknowledgement,
)
from pi_card.pipeline.capture import SilenceTimeout, Utterance, capture_utterance
from pi_card.pipeline.stt import WhisperSTT
from pi_card.pipeline.tts import PiperTTS

SYSTEM_PROMPT = (
    "You are a concise voice assistant. Reply in 1\u20133 sentences unless asked for detail. "
    "Avoid markdown, lists, or code \u2014 your output is spoken aloud."
)

_logger = logging.getLogger(__name__)
_transcripts = logging.getLogger("pi_card.transcripts")


class Conversation:
    """One session: wake-to-goodbye/timeout. Holds message history and the live language."""

    def __init__(
        self,
        *,
        audio_in: AudioInput,
        audio_out: AudioOutput,
        leds: LEDController,
        agent: AIAgent,
        stt: WhisperSTT,
        tts_by_language: dict[str, PiperTTS],
        initial_language: str,
        silence_timeout_ms: int,
        max_stt_retries: int,
    ):
        self._audio_in = audio_in
        self._audio_out = audio_out
        self._leds = leds
        self._agent = agent
        self._stt = stt
        self._tts_by_language = tts_by_language
        self._language = initial_language
        self._silence_timeout_ms = silence_timeout_ms
        self._max_stt_retries = max_stt_retries
        self._history: list[Message] = [Message(role="system", content=SYSTEM_PROMPT)]

    def run(self) -> str:
        """Run turns until silence timeout, exit phrase, or error. Returns the final language."""
        while self._run_one_turn():
            pass
        self._leds.set_state(LEDState.OFF)
        return self._language

    def _run_one_turn(self) -> bool:
        """Return True to continue the conversation, False to end it."""
        text = self._listen_and_transcribe()
        if text is None:
            return False

        _transcripts.info("user (%s): %s", self._language, text)

        if is_exit_phrase(text, language=self._language):
            return False

        switch_target = detect_language_switch(text, current_language=self._language)
        if switch_target is not None:
            self._language = switch_target
            return self._speak(switch_acknowledgement(language=switch_target), language=switch_target)

        self._history.append(Message(role="user", content=text))
        try:
            reply = self._agent.chat(self._history)
        except Exception:
            _logger.exception("agent call failed")
            self._announce_network_failure()
            return False
        self._history.append(reply)

        _transcripts.info("assistant (%s): %s", self._language, reply.content or "")
        return self._speak(reply.content or "", language=self._language)

    def _listen_and_transcribe(self) -> str | None:
        """Capture an utterance and transcribe it, retrying on low confidence.

        Returns the transcript on success, or None when the conversation should end
        (silence timeout, retries exhausted, or a secondary TTS failure).
        """
        for attempt in range(self._max_stt_retries + 1):
            self._leds.set_state(LEDState.LISTENING)
            result = capture_utterance(
                self._audio_in,
                silence_ms_no_speech=self._silence_timeout_ms,
            )
            if isinstance(result, SilenceTimeout):
                return None

            assert isinstance(result, Utterance)
            self._leds.set_state(LEDState.THINKING)
            text = self._stt.transcribe(result.pcm, language=self._language)
            if text:
                return text

            if attempt < self._max_stt_retries:
                if not self._speak(
                    repeat_prompt(language=self._language), language=self._language
                ):
                    return None

        self._play_error_tone()
        return None

    def _speak(self, text: str, *, language: str) -> bool:
        """Speak `text` through the language's TTS. Returns False on failure."""
        self._leds.set_state(LEDState.OFF)
        try:
            self._tts_by_language[language].speak(text, self._audio_out)
            return True
        except Exception:
            _logger.exception("TTS speak failed (language=%s)", language)
            self._play_error_tone()
            return False

    def _announce_network_failure(self) -> None:
        self._leds.set_state(LEDState.ERROR)
        try:
            self._tts_by_language[self._language].speak(
                network_error_cue(language=self._language), self._audio_out
            )
        except Exception:
            _logger.exception("network-error cue TTS failed")
            self._audio_out.play(error_tone())

    def _play_error_tone(self) -> None:
        self._leds.set_state(LEDState.ERROR)
        self._audio_out.play(error_tone())
