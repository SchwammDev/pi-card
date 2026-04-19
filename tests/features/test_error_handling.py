from pi_card.audio_tones import error_tone
from pi_card.hardware.leds import LEDState

from tests.dsl.actions import (
    agent_call_will_fail,
    assistant_will_reply,
    run_until_exhausted,
    trigger_wake_word,
    tts_will_fail,
    user_says,
)
from tests.dsl.assertions import (
    assert_agent_was_called,
    assert_assistant_spoke,
    assert_led_went_through,
    assert_returned_to_wake_word_mode,
)


def test_network_failure_speaks_cue_flashes_red_and_returns_to_wake_word_mode(world):
    trigger_wake_word(world)
    user_says(world, "Hello", language="en")
    agent_call_will_fail(world, ConnectionError("no network"))

    run_until_exhausted(world)

    assert_assistant_spoke(world, containing="can't reach my brain", language="en")
    assert_led_went_through(world, LEDState.ERROR)
    assert_returned_to_wake_word_mode(world)


def test_network_failure_cue_is_spoken_in_the_current_language(world):
    trigger_wake_word(world)
    user_says(world, "switch to French", language="en")
    user_says(world, "Bonjour", language="fr")
    agent_call_will_fail(world, ConnectionError("no network"))

    run_until_exhausted(world)

    assert_assistant_spoke(world, containing="cerveau", language="fr")


def test_low_confidence_stt_prompts_user_to_repeat_and_retries(world):
    trigger_wake_word(world)
    # First utterance: whisper returns "" (we don't set a transcript) = low confidence
    user_says(world, "", language="en")
    # Second utterance: user repeats successfully
    user_says(world, "What's the weather?", language="en")
    assistant_will_reply(world, "Sunny.")

    run_until_exhausted(world)

    assert_assistant_spoke(world, containing="repeat", language="en")
    assert_agent_was_called(world, times=1)  # only the successful retry reached the agent


def test_low_confidence_stt_gives_up_after_max_retries_and_flashes_red(world):
    trigger_wake_word(world)
    # Exceed retries: queue three failed utterances (initial + 2 retries = 3 attempts)
    user_says(world, "", language="en")
    user_says(world, "", language="en")
    user_says(world, "", language="en")

    run_until_exhausted(world)

    assert_led_went_through(world, LEDState.ERROR)
    assert_returned_to_wake_word_mode(world)
    assert_agent_was_called(world, times=0)


def test_tts_failure_plays_error_tone_and_returns_to_wake_word_mode(world):
    trigger_wake_word(world)
    user_says(world, "Hello", language="en")
    assistant_will_reply(world, "Hi there.")
    tts_will_fail(world, language="en", exception=RuntimeError("tts boom"))

    run_until_exhausted(world)

    assert error_tone() in world.audio_out.played
    assert_led_went_through(world, LEDState.ERROR)
    assert_returned_to_wake_word_mode(world)


def test_led_goes_red_then_off_on_error(world):
    trigger_wake_word(world)
    user_says(world, "Hello", language="en")
    agent_call_will_fail(world, ConnectionError("no network"))

    run_until_exhausted(world)

    assert_led_went_through(world, LEDState.ERROR, LEDState.OFF)
