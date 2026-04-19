from pi_card.hardware.audio_input import (
    AudioInputExhausted,
    FRAME_BYTES,
    FRAME_DURATION_MS,
)

from tests.dsl.world import World

_SILENCE_FRAME = b"\x00" * FRAME_BYTES
_SPEECH_FRAME = b"\x00\x10" * (FRAME_BYTES // 2)  # amplitude 4096 samples


def trigger_wake_word(world: World) -> None:
    """Arm the wake-word engine so the next frame read crosses the threshold."""
    world.wake_word_engine.queue_score(0.9)
    world.audio_in.queue(_SILENCE_FRAME)


def user_says(world: World, text: str, *, language: str) -> None:
    """Queue speech-shaped audio + trailing silence, and queue the STT transcript for the language."""
    world.audio_in.queue(_SPEECH_FRAME * 2)
    world.audio_in.queue(_SILENCE_FRAME * 8)
    world.whisper.queue_transcript(language, text)


def user_stays_silent(world: World, *, ms: int = 800) -> None:
    """Queue silence long enough for the conversation's silence timeout to fire."""
    frames = max(1, ms // FRAME_DURATION_MS)
    world.audio_in.queue(_SILENCE_FRAME * frames)


def assistant_will_reply(world: World, text: str) -> None:
    """Queue a canned reply from the fake agent."""
    world.agent.queue(text)


def agent_call_will_fail(world: World, exception: Exception) -> None:
    """Install a next-call exception on the fake agent."""
    original_chat = world.agent.chat
    raised = {"done": False}

    def _failing_chat(messages):
        if not raised["done"]:
            raised["done"] = True
            raise exception
        return original_chat(messages)

    world.agent.chat = _failing_chat  # type: ignore[method-assign]


def tts_will_fail(world: World, *, language: str, exception: Exception) -> None:
    """Make the next synthesize() call on the given language's voice raise."""
    voice = world.voices[language]
    original_synthesize = voice.synthesize
    raised = {"done": False}

    def _failing_synthesize(text):
        if not raised["done"]:
            raised["done"] = True
            raise exception
        return original_synthesize(text)

    voice.synthesize = _failing_synthesize  # type: ignore[method-assign]


def run_until_exhausted(world: World) -> None:
    """Run the assistant until the fake audio stream is empty."""
    try:
        world.assistant.run()
    except AudioInputExhausted:
        pass
