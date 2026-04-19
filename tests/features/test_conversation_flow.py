from pi_card.hardware.leds import LEDState

from tests.dsl.actions import (
    assistant_will_reply,
    run_until_exhausted,
    trigger_wake_word,
    user_says,
    user_stays_silent,
)
from tests.dsl.assertions import (
    assert_agent_last_saw_user_message,
    assert_agent_was_called,
    assert_agent_was_not_called,
    assert_assistant_did_not_speak_in,
    assert_assistant_spoke,
    assert_conversation_started_fresh_at_call,
    assert_history_accumulated_within_conversation,
    assert_last_call_included_prior_assistant_reply,
    assert_led_went_through,
    assert_returned_to_wake_word_mode,
)


def test_responds_to_a_single_question_after_the_wake_word(world):
    trigger_wake_word(world)
    user_says(world, "What's the weather?", language="en")
    assistant_will_reply(world, "It's sunny today.")

    run_until_exhausted(world)

    assert_assistant_spoke(world, containing="sunny", language="en")
    assert_agent_last_saw_user_message(world, "What's the weather?")


def test_stays_open_for_a_follow_up_after_the_first_response(world):
    trigger_wake_word(world)
    user_says(world, "What's the weather?", language="en")
    assistant_will_reply(world, "It's sunny today.")
    user_says(world, "Will it rain tomorrow?", language="en")
    assistant_will_reply(world, "No rain expected.")

    run_until_exhausted(world)

    assert_agent_was_called(world, times=2)
    assert_assistant_spoke(world, containing="sunny", language="en")
    assert_assistant_spoke(world, containing="No rain", language="en")


def test_conversation_history_accumulates_across_follow_ups(world):
    trigger_wake_word(world)
    user_says(world, "My name is Alice.", language="en")
    assistant_will_reply(world, "Nice to meet you, Alice.")
    user_says(world, "What is my name?", language="en")
    assistant_will_reply(world, "Your name is Alice.")

    run_until_exhausted(world)

    assert_history_accumulated_within_conversation(world)
    assert_last_call_included_prior_assistant_reply(world, "Nice to meet you")


def test_returns_to_wake_word_mode_after_silence_timeout(world):
    trigger_wake_word(world)
    user_says(world, "Hello", language="en")
    assistant_will_reply(world, "Hi there.")
    user_stays_silent(world, ms=800)

    run_until_exhausted(world)

    assert_agent_was_called(world, times=1)
    assert_returned_to_wake_word_mode(world)


def test_returns_to_wake_word_mode_on_explicit_exit_phrase(world):
    trigger_wake_word(world)
    user_says(world, "Hello", language="en")
    assistant_will_reply(world, "Hi there.")
    user_says(world, "Goodbye", language="en")

    run_until_exhausted(world)

    assert_agent_was_called(world, times=1)
    assert_returned_to_wake_word_mode(world)


def test_history_is_reset_between_conversations(world):
    trigger_wake_word(world)
    user_says(world, "My name is Alice.", language="en")
    assistant_will_reply(world, "Nice to meet you, Alice.")
    user_says(world, "Goodbye", language="en")

    trigger_wake_word(world)
    user_says(world, "What's the weather?", language="en")
    assistant_will_reply(world, "Sunny.")

    run_until_exhausted(world)

    # First conversation: 1 agent call. Second conversation: 1 agent call.
    assert_agent_was_called(world, times=2)
    # Second conversation's first call should be fresh (system + user only).
    assert_conversation_started_fresh_at_call(world, call_index=1)


def test_led_cycle_for_a_single_turn(world):
    trigger_wake_word(world)
    user_says(world, "Hello", language="en")
    assistant_will_reply(world, "Hi.")

    run_until_exhausted(world)

    assert_led_went_through(
        world,
        LEDState.LISTENING,   # capturing user utterance
        LEDState.THINKING,    # STT + agent call
        LEDState.OFF,         # speaking
    )


def test_switches_to_french_mid_session(world):
    trigger_wake_word(world)
    user_says(world, "Hello", language="en")
    assistant_will_reply(world, "Hi.")
    user_says(world, "switch to French", language="en")
    user_says(world, "Quel temps fait-il?", language="fr")
    assistant_will_reply(world, "Il fait beau.")

    run_until_exhausted(world)

    assert_assistant_spoke(world, containing="français", language="fr")
    assert_assistant_spoke(world, containing="Il fait beau", language="fr")


def test_switches_to_english_mid_session(world):
    # Start in French via explicit construction would require a new fixture; instead,
    # trigger EN→FR first to get into French state, then FR→EN.
    trigger_wake_word(world)
    user_says(world, "switch to French", language="en")
    user_says(world, "parle anglais", language="fr")
    user_says(world, "Hello again", language="en")
    assistant_will_reply(world, "Welcome back.")

    run_until_exhausted(world)

    assert_assistant_spoke(world, containing="English", language="en")
    assert_assistant_spoke(world, containing="Welcome back", language="en")


def test_language_switch_commands_are_not_sent_to_the_agent(world):
    trigger_wake_word(world)
    user_says(world, "switch to French", language="en")
    user_says(world, "Quel temps fait-il?", language="fr")
    assistant_will_reply(world, "Il fait beau.")

    run_until_exhausted(world)

    assert_agent_was_called(world, times=1)
    assert_agent_last_saw_user_message(world, "Quel temps fait-il?")


def test_exit_phrase_is_not_sent_to_the_agent(world):
    trigger_wake_word(world)
    user_says(world, "Hello", language="en")
    assistant_will_reply(world, "Hi.")
    user_says(world, "Goodbye", language="en")

    run_until_exhausted(world)

    assert_agent_was_called(world, times=1)


def test_wake_word_command_alone_with_no_speech_returns_to_wake_word_mode(world):
    trigger_wake_word(world)
    user_stays_silent(world, ms=800)

    run_until_exhausted(world)

    assert_agent_was_not_called(world)
    assert_assistant_did_not_speak_in(world, "en")
    assert_returned_to_wake_word_mode(world)
