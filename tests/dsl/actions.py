from pi_card.hardware.audio_input import (
    AudioInputExhausted,
    FRAME_BYTES,
    FRAME_DURATION_MS,
)

from tests.dsl.world import World

_SILENCE_FRAME = b"\x00" * FRAME_BYTES
_SPEECH_FRAME = b"\x01" * FRAME_BYTES

_USER_SAYS_SPEECH_FRAMES = 2
_USER_SAYS_TRAILING_SILENCE_FRAMES = 8


def trigger_wake_word(world: World) -> None:
    """Arm the wake-word engine so the next frame read crosses the threshold."""
    world.wake_word_engine.queue_score(0.9)
    world.audio_in.queue(_SILENCE_FRAME)


def user_says(world: World, text: str, *, language: str) -> None:
    """Queue speech-shaped audio + trailing silence, and queue the STT transcript for the language."""
    world.audio_in.queue(_SPEECH_FRAME * _USER_SAYS_SPEECH_FRAMES)
    world.audio_in.queue(_SILENCE_FRAME * _USER_SAYS_TRAILING_SILENCE_FRAMES)
    world.speech_detector.queue(
        *([True] * _USER_SAYS_SPEECH_FRAMES),
        *([False] * _USER_SAYS_TRAILING_SILENCE_FRAMES),
    )
    world.whisper.queue_transcript(language, text)


def user_stays_silent(world: World, *, ms: int = 800) -> None:
    """Queue silence long enough for the conversation's silence timeout to fire."""
    frames = max(1, ms // FRAME_DURATION_MS)
    world.audio_in.queue(_SILENCE_FRAME * frames)
    world.speech_detector.queue(*([False] * frames))


def assistant_will_reply(world: World, text: str) -> None:
    """Queue a canned reply from the fake agent."""
    world.agent.queue(text)


def assistant_will_stream_reply(world: World, deltas: list[str]) -> None:
    world.agent.queue(deltas)


def agent_call_will_fail(world: World, exception: Exception) -> None:
    """Install a next-call exception on the fake agent."""
    original_stream = world.agent.stream
    raised = {"done": False}

    def _failing_stream(messages):
        if not raised["done"]:
            raised["done"] = True
            raise exception
        return original_stream(messages)

    world.agent.stream = _failing_stream  # type: ignore[method-assign]


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
