import pytest

from pi_card.assistant import VoiceAssistant
from pi_card.pipeline.stt import WhisperSTT
from pi_card.pipeline.tts import PiperTTS
from pi_card.pipeline.wake_word import WakeWordDetector

from tests.dsl.world import World
from tests.fakes.ai_agent import FakeAIAgent
from tests.fakes.audio_input import FakeAudioInput
from tests.fakes.audio_output import FakeAudioOutput
from tests.fakes.leds import FakeLEDController
from tests.fakes.piper_voice import FakePiperVoice
from tests.fakes.wake_word_engine import FakeWakeWordEngine
from tests.fakes.whisper_model import FakeWhisperModel


@pytest.fixture
def fake_audio_in():
    return FakeAudioInput()


@pytest.fixture
def fake_audio_out():
    return FakeAudioOutput()


@pytest.fixture
def fake_leds():
    return FakeLEDController()


@pytest.fixture
def fake_agent():
    return FakeAIAgent()


@pytest.fixture
def fake_wake_word_engine():
    return FakeWakeWordEngine()


@pytest.fixture
def fake_whisper_model():
    return FakeWhisperModel()


@pytest.fixture
def fake_en_voice():
    return FakePiperVoice()


@pytest.fixture
def fake_fr_voice():
    return FakePiperVoice()


@pytest.fixture
def assistant(
    fake_audio_in,
    fake_audio_out,
    fake_leds,
    fake_agent,
    fake_wake_word_engine,
    fake_whisper_model,
    fake_en_voice,
    fake_fr_voice,
):
    return VoiceAssistant(
        audio_in=fake_audio_in,
        audio_out=fake_audio_out,
        leds=fake_leds,
        agent=fake_agent,
        wake_word_detector=WakeWordDetector(engine=fake_wake_word_engine),
        stt=WhisperSTT(model=fake_whisper_model),
        tts_by_language={
            "en": PiperTTS(voice=fake_en_voice),
            "fr": PiperTTS(voice=fake_fr_voice),
        },
        language="en",
        silence_timeout=0.5,
        max_stt_retries=2,
    )


@pytest.fixture
def world(
    assistant,
    fake_audio_in,
    fake_audio_out,
    fake_leds,
    fake_agent,
    fake_wake_word_engine,
    fake_whisper_model,
    fake_en_voice,
    fake_fr_voice,
):
    return World(
        assistant=assistant,
        audio_in=fake_audio_in,
        audio_out=fake_audio_out,
        leds=fake_leds,
        agent=fake_agent,
        wake_word_engine=fake_wake_word_engine,
        whisper=fake_whisper_model,
        voices={"en": fake_en_voice, "fr": fake_fr_voice},
    )
