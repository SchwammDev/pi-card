import pytest

from pi_card.assistant import VoiceAssistant

from tests.fakes.audio_input import FakeAudioInput
from tests.fakes.audio_output import FakeAudioOutput
from tests.fakes.leds import FakeLEDController
from tests.fakes.ai_agent import FakeAIAgent


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
def assistant(fake_audio_in, fake_audio_out, fake_leds, fake_agent):
    return VoiceAssistant(
        audio_in=fake_audio_in,
        audio_out=fake_audio_out,
        leds=fake_leds,
        agent=fake_agent,
    )
