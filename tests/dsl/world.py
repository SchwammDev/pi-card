from dataclasses import dataclass

from pi_card.assistant import VoiceAssistant

from tests.fakes.ai_agent import FakeAIAgent
from tests.fakes.audio_input import FakeAudioInput
from tests.fakes.audio_output import FakeAudioOutput
from tests.fakes.leds import FakeLEDController
from tests.fakes.piper_voice import FakePiperVoice
from tests.fakes.wake_word_engine import FakeWakeWordEngine
from tests.fakes.whisper_model import FakeWhisperModel


@dataclass
class World:
    """Bundle of fakes + the assistant under test, shared across DSL helpers."""

    assistant: VoiceAssistant
    audio_in: FakeAudioInput
    audio_out: FakeAudioOutput
    leds: FakeLEDController
    agent: FakeAIAgent
    wake_word_engine: FakeWakeWordEngine
    whisper: FakeWhisperModel
    voices: dict[str, FakePiperVoice]
