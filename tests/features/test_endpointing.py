from dataclasses import dataclass

import pytest

from pi_card.conversation import Conversation
from pi_card.hardware.audio_input import FRAME_BYTES, FRAME_SAMPLES
from pi_card.pipeline.stt import WhisperSTT
from pi_card.pipeline.tts import PiperTTS
from tests.fakes.speech_detector import ScriptedSpeechDetector


SPEECH_FRAME = b"\x01" * FRAME_BYTES
SILENCE_FRAME = b"\x00" * FRAME_BYTES


def test_natural_pause_in_speech_does_not_end_the_user_turn_early(scenario):
    user_speaks_with_a_natural_one_second_pause(scenario)

    run_one_turn(scenario, min_silence_duration_ms=1500)

    assert_stt_received_at_least_frames(scenario, frames=30)


@dataclass
class Scenario:
    audio_in: object
    audio_out: object
    leds: object
    agent: object
    whisper: object
    en_voice: object
    fr_voice: object
    speech_detector: ScriptedSpeechDetector


@pytest.fixture
def scenario(
    fake_audio_in, fake_audio_out, fake_leds, fake_agent,
    fake_whisper_model, fake_en_voice, fake_fr_voice, fake_speech_detector,
):
    fake_whisper_model.set_transcript("en", "hello")
    fake_agent.queue("hi")
    return Scenario(
        audio_in=fake_audio_in, audio_out=fake_audio_out, leds=fake_leds,
        agent=fake_agent, whisper=fake_whisper_model,
        en_voice=fake_en_voice, fr_voice=fake_fr_voice,
        speech_detector=fake_speech_detector,
    )


def user_speaks_with_a_natural_one_second_pause(scenario: Scenario) -> None:
    pattern = "VV" + "S" * 13 + "VV" + "S" * 100
    frames = {"V": SPEECH_FRAME, "S": SILENCE_FRAME}
    scenario.audio_in.queue(b"".join(frames[c] for c in pattern))
    scenario.speech_detector.queue(*[c == "V" for c in pattern])


def run_one_turn(scenario: Scenario, *, min_silence_duration_ms: int) -> None:
    Conversation(
        audio_in=scenario.audio_in,
        audio_out=scenario.audio_out,
        leds=scenario.leds,
        agent=scenario.agent,
        stt=WhisperSTT(model=scenario.whisper),
        tts_by_language={
            "en": PiperTTS(voice=scenario.en_voice),
            "fr": PiperTTS(voice=scenario.fr_voice),
        },
        speech_detector=scenario.speech_detector,
        initial_language="en",
        silence_timeout_ms=500,
        max_stt_retries=2,
        min_silence_duration_ms=min_silence_duration_ms,
    ).run()


def assert_stt_received_at_least_frames(scenario: Scenario, *, frames: int) -> None:
    assert scenario.whisper.calls, "expected capture to commit a turn so STT runs"
    received = scenario.whisper.calls[0]["num_samples"]
    assert received >= frames * FRAME_SAMPLES, (
        f"STT received {received} samples; expected at least {frames * FRAME_SAMPLES} "
        f"(captured turn was truncated by endpointing)"
    )
