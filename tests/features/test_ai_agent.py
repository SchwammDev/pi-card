from tests.dsl.actions import (
    assistant_will_reply,
    run_until_exhausted,
    trigger_wake_word,
    user_says,
)
from tests.dsl.assertions import (
    assert_agent_last_saw_user_message,
    assert_agent_was_called,
    assert_every_agent_call_started_with_system_prompt,
    assert_last_call_included_prior_assistant_reply,
)


SYSTEM_PROMPT = (
    "You are a concise voice assistant. Reply in 1\u20133 sentences unless asked for detail. "
    "Avoid markdown, lists, or code \u2014 your output is spoken aloud."
)


def test_every_agent_call_starts_with_the_spec_system_prompt(world):
    trigger_wake_word(world)
    user_says(world, "Hello", language="en")
    assistant_will_reply(world, "Hi.")
    user_says(world, "How are you?", language="en")
    assistant_will_reply(world, "Doing well.")

    run_until_exhausted(world)

    assert_every_agent_call_started_with_system_prompt(world)
    for call in world.agent.received:
        assert call[0].content == SYSTEM_PROMPT


def test_user_utterance_is_sent_with_role_user(world):
    trigger_wake_word(world)
    user_says(world, "What's the weather?", language="en")
    assistant_will_reply(world, "Sunny.")

    run_until_exhausted(world)

    assert_agent_last_saw_user_message(world, "What's the weather?")


def test_prior_assistant_reply_is_threaded_into_the_next_agent_call(world):
    trigger_wake_word(world)
    user_says(world, "My favourite colour is blue.", language="en")
    assistant_will_reply(world, "Got it, blue.")
    user_says(world, "What is my favourite colour?", language="en")
    assistant_will_reply(world, "Blue.")

    run_until_exhausted(world)

    assert_agent_was_called(world, times=2)
    assert_last_call_included_prior_assistant_reply(world, "Got it, blue")
