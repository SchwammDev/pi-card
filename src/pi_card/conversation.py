import logging
import time
from typing import Iterable, Iterator

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
from pi_card.pipeline.sentence_chunker import chunk_sentences
from pi_card.pipeline.speech_detector import SpeechDetector
from pi_card.pipeline.stt import SpeechToText
from pi_card.pipeline.tts import PiperTTS, TTSError

SYSTEM_PROMPT = (
    "You are a concise voice assistant. Reply in 1\u20133 sentences unless asked for detail. "
    "Avoid markdown, lists, or code \u2014 your output is spoken aloud."
)

_logger = logging.getLogger(__name__)
_transcripts = logging.getLogger("pi_card.transcripts")
_latency = logging.getLogger("pi_card.latency")


class Conversation:
    """One session: wake-to-goodbye/timeout. Holds message history and the live language."""

    def __init__(
        self,
        *,
        audio_in: AudioInput,
        audio_out: AudioOutput,
        leds: LEDController,
        agent: AIAgent,
        stt: SpeechToText,
        tts_by_language: dict[str, PiperTTS],
        speech_detector: SpeechDetector,
        initial_language: str,
        silence_timeout_ms: int,
        max_stt_retries: int,
        min_silence_duration_ms: int,
    ):
        self._audio_in = audio_in
        self._audio_out = audio_out
        self._leds = leds
        self._agent = agent
        self._stt = stt
        self._tts_by_language = tts_by_language
        self._speech_detector = speech_detector
        self._language = initial_language
        self._silence_timeout_ms = silence_timeout_ms
        self._max_stt_retries = max_stt_retries
        self._min_silence_duration_ms = min_silence_duration_ms
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
        return self._stream_reply_to_speech()

    def _stream_reply_to_speech(self) -> bool:
        voice = self._tts_by_language[self._language]
        spoken_chunks: list[str] = []
        t0 = self._t_thinking_on

        def _on_first_audio() -> None:
            _latency.info("first_audio +%.3fs", time.perf_counter() - t0)
            self._leds.set_state(LEDState.OFF)

        try:
            deltas = _log_first(self._agent.stream(self._history), "first_token", t0)
            chunks = _log_first(chunk_sentences(deltas), "first_chunk", t0)
            for spoken in voice.speak_stream(
                chunks,
                self._audio_out,
                on_first_audio=_on_first_audio,
            ):
                spoken_chunks.append(spoken)
        except TTSError:
            _logger.exception("TTS speak_stream failed (language=%s)", self._language)
            self._record_spoken_reply(spoken_chunks)
            self._play_error_tone()
            return False
        except Exception:
            _logger.exception("agent stream failed")
            self._record_spoken_reply(spoken_chunks)
            self._announce_network_failure()
            return False

        self._record_spoken_reply(spoken_chunks)
        return True

    def _record_spoken_reply(self, spoken_chunks: list[str]) -> None:
        if not spoken_chunks:
            return
        content = " ".join(spoken_chunks)
        self._history.append(Message(role="assistant", content=content))
        _transcripts.info("assistant (%s): %s", self._language, content)

    def _listen_and_transcribe(self) -> str | None:
        """Capture an utterance and transcribe it, retrying on low confidence.

        Returns the transcript on success, or None when the conversation should end
        (silence timeout, retries exhausted, or a secondary TTS failure).
        """
        for attempt in range(self._max_stt_retries + 1):
            self._leds.set_state(LEDState.LISTENING)
            self._audio_in.drain_pending()
            result = capture_utterance(
                self._audio_in,
                self._speech_detector,
                silence_ms_no_speech=self._silence_timeout_ms,
                silence_ms_after_speech=self._min_silence_duration_ms,
            )
            if isinstance(result, SilenceTimeout):
                return None

            assert isinstance(result, Utterance)
            self._leds.set_state(LEDState.THINKING)
            self._t_thinking_on = time.perf_counter()
            transcript = self._stt.transcribe(result.pcm, language=self._language)
            if transcript.text:
                _latency.info("stt_done +%.3fs", time.perf_counter() - self._t_thinking_on)
                return transcript.text

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


def _log_first(items: Iterable[str], label: str, t0: float) -> Iterator[str]:
    seen = False
    for item in items:
        if not seen:
            _latency.info("%s +%.3fs", label, time.perf_counter() - t0)
            seen = True
        yield item
