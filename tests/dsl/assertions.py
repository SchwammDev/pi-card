from pi_card.hardware.ai_agent import Message
from pi_card.hardware.leds import LEDState

from tests.dsl.world import World


def assert_assistant_spoke(world: World, *, containing: str, language: str) -> None:
    voice = world.voices[language]
    if not any(containing in text for text in voice.synthesized):
        raise AssertionError(
            f"expected assistant to speak text containing {containing!r} in {language}; "
            f"got {voice.synthesized!r}"
        )


def assert_assistant_did_not_speak_in(world: World, language: str) -> None:
    voice = world.voices[language]
    if voice.synthesized:
        raise AssertionError(
            f"expected no TTS output in {language}; got {voice.synthesized!r}"
        )


def assert_led_went_through(world: World, *expected_states: LEDState) -> None:
    """Assert the expected states appear in the given order inside the LED history (not necessarily contiguous)."""
    states = world.leds.states
    cursor = 0
    for expected in expected_states:
        try:
            cursor = states.index(expected, cursor) + 1
        except ValueError as exc:
            raise AssertionError(
                f"expected LED states {list(expected_states)!r} to appear in order; "
                f"got {states!r}"
            ) from exc


def assert_returned_to_wake_word_mode(world: World) -> None:
    if not world.leds.states or world.leds.states[-1] != LEDState.OFF:
        raise AssertionError(
            f"expected LEDs to end at OFF (back in wake-word mode); "
            f"got {world.leds.states!r}"
        )


def assert_agent_was_called(world: World, *, times: int) -> None:
    actual = len(world.agent.received)
    if actual != times:
        raise AssertionError(
            f"expected agent to be called {times} time(s); got {actual}"
        )


def assert_agent_was_not_called(world: World) -> None:
    assert_agent_was_called(world, times=0)


def assert_agent_last_saw_user_message(world: World, text: str) -> None:
    last_call = world.agent.received[-1]
    user_contents = [m.content for m in last_call if m.role == "user"]
    if text not in user_contents:
        raise AssertionError(
            f"expected user message {text!r} in last agent call; got {user_contents!r}"
        )


def assert_every_agent_call_started_with_system_prompt(world: World) -> None:
    for i, call in enumerate(world.agent.received):
        if not call or call[0].role != "system":
            raise AssertionError(
                f"agent call #{i} did not start with a system prompt; got {call!r}"
            )


def assert_history_accumulated_within_conversation(world: World) -> None:
    """Each subsequent agent call within a conversation should include the prior turn's messages."""
    sizes = [len(call) for call in world.agent.received]
    if sizes != sorted(sizes) or len(set(sizes)) != len(sizes):
        raise AssertionError(
            f"expected agent message history to grow monotonically; got sizes {sizes!r}"
        )


def assert_conversation_started_fresh_at_call(world: World, call_index: int) -> None:
    """The agent call at `call_index` should have exactly [system, user] — no prior history."""
    call = world.agent.received[call_index]
    if len(call) != 2 or call[0].role != "system" or call[1].role != "user":
        raise AssertionError(
            f"expected fresh conversation (system + user) at call #{call_index}; got {call!r}"
        )


def _assistant_messages_in(call: list[Message]) -> list[str]:
    return [m.content or "" for m in call if m.role == "assistant"]


def assert_last_call_included_prior_assistant_reply(world: World, text: str) -> None:
    last_call = world.agent.received[-1]
    if not any(text in reply for reply in _assistant_messages_in(last_call)):
        raise AssertionError(
            f"expected last agent call to include prior assistant reply containing {text!r}; "
            f"got {_assistant_messages_in(last_call)!r}"
        )
