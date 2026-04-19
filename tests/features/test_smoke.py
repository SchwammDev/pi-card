from pi_card.hardware.audio_input import AudioInput
from pi_card.hardware.audio_output import AudioOutput
from pi_card.hardware.leds import LEDController
from pi_card.hardware.ai_agent import AIAgent


def test_fakes_satisfy_their_hardware_contracts(
    fake_audio_in, fake_audio_out, fake_leds, fake_agent
):
    assert isinstance(fake_audio_in, AudioInput)
    assert isinstance(fake_audio_out, AudioOutput)
    assert isinstance(fake_leds, LEDController)
    assert isinstance(fake_agent, AIAgent)


def test_assistant_wires_fake_hardware_through_its_constructor(
    assistant, fake_audio_in, fake_audio_out, fake_leds, fake_agent
):
    assert assistant.audio_in is fake_audio_in
    assert assistant.audio_out is fake_audio_out
    assert assistant.leds is fake_leds
    assert assistant.agent is fake_agent
