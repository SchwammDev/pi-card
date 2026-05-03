from dataclasses import dataclass

import pytest

from pi_card.conversation import Conversation
from pi_card.hardware.audio_input import FRAME_BYTES, FRAME_SAMPLES
from pi_card.pipeline.stt import WhisperSTT
from pi_card.pipeline.tts import PiperTTS


def _frame_at_amplitude(amplitude: int) -> bytes:
    return amplitude.to_bytes(2, "little", signed=True) * (FRAME_BYTES // 2)


SILENCE_FRAME = _frame_at_amplitude(0)
SPEECH_FRAME = _frame_at_amplitude(8192)
QUIET_SPEECH_FRAME = _frame_at_amplitude(1000)


def test_natural_pause_in_speech_does_not_end_the_user_turn_early(scenario):
    user_speaks_with_a_natural_one_second_pause(scenario)

    run_one_turn(scenario, pause_tolerance_ms=1500, speech_rms_threshold=1500)

    assert_stt_received_at_least_frames(scenario, frames=30)


def test_quieter_speech_is_recognized_when_the_speech_threshold_is_lowered(scenario):
    user_speaks_quietly(scenario)

    run_one_turn(scenario, pause_tolerance_ms=1500, speech_rms_threshold=500)

    assert_stt_received_at_least_frames(scenario, frames=4)


@dataclass
class Scenario:
    audio_in: object
    audio_out: object
    leds: object
    agent: object
    whisper: object
    en_voice: object
    fr_voice: object


@pytest.fixture
def scenario(
    fake_audio_in, fake_audio_out, fake_leds, fake_agent,
    fake_whisper_model, fake_en_voice, fake_fr_voice,
):
    fake_whisper_model.set_transcript("en", "hello")
    fake_agent.queue("hi")
    return Scenario(
        audio_in=fake_audio_in, audio_out=fake_audio_out, leds=fake_leds,
        agent=fake_agent, whisper=fake_whisper_model,
        en_voice=fake_en_voice, fr_voice=fake_fr_voice,
    )


def user_speaks_with_a_natural_one_second_pause(scenario: Scenario) -> None:
    scenario.audio_in.queue(
        SPEECH_FRAME * 2 + SILENCE_FRAME * 13 + SPEECH_FRAME * 2 + SILENCE_FRAME * 100
    )


def user_speaks_quietly(scenario: Scenario) -> None:
    scenario.audio_in.queue(QUIET_SPEECH_FRAME * 4 + SILENCE_FRAME * 100)


def run_one_turn(scenario: Scenario, *, pause_tolerance_ms: int, speech_rms_threshold: int) -> None:
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
        initial_language="en",
        silence_timeout_ms=500,
        max_stt_retries=2,
        pause_tolerance_ms=pause_tolerance_ms,
        speech_rms_threshold=speech_rms_threshold,
    ).run()


def assert_stt_received_at_least_frames(scenario: Scenario, *, frames: int) -> None:
    assert scenario.whisper.calls, "expected capture to commit a turn so STT runs"
    received = scenario.whisper.calls[0]["num_samples"]
    assert received >= frames * FRAME_SAMPLES, (
        f"STT received {received} samples; expected at least {frames * FRAME_SAMPLES} "
        f"(captured turn was truncated by endpointing)"
    )
