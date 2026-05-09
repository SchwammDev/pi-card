import threading

import pytest

from pi_card.pipeline.tts import PiperTTS, TTSError


class _BlockingSink:
    def __init__(self):
        self.played: list[bytes] = []
        self.play_started = threading.Event()
        self.play_can_finish = threading.Event()

    def play(self, pcm: bytes) -> None:
        self.played.append(pcm)
        self.play_started.set()
        self.play_can_finish.wait(timeout=2.0)


class _ImmediateSink:
    def __init__(self):
        self.played: list[bytes] = []

    def play(self, pcm: bytes) -> None:
        self.played.append(pcm)


class _TrackingVoice:
    sample_rate = 16_000

    def __init__(self):
        self.synthesized: list[str] = []
        self.second_synth_done = threading.Event()

    def synthesize(self, text: str) -> bytes:
        self.synthesized.append(text)
        if len(self.synthesized) == 2:
            self.second_synth_done.set()
        return b"PCM_" + text.encode()


class _ExplodingVoice:
    sample_rate = 16_000

    def synthesize(self, text):
        raise RuntimeError("piper exploded")


class _ExplodingSink:
    def play(self, pcm):
        raise RuntimeError("alsa exploded")


class _Boom(Exception):
    pass


def _two_long_sentences():
    return iter(["first long enough sentence", "second long enough sentence"])


def _consume_in_background(iterator):
    def runner():
        for _ in iterator:
            pass

    thread = threading.Thread(target=runner)
    thread.start()
    return thread


def assert_second_synth_completes_while_first_play_blocks(tts, voice, sink):
    consumer = _consume_in_background(tts.speak_stream(_two_long_sentences(), sink))
    try:
        assert sink.play_started.wait(timeout=2.0)
        assert voice.second_synth_done.wait(timeout=2.0)
    finally:
        sink.play_can_finish.set()
        consumer.join(timeout=2.0)


def test_next_chunk_is_synthesized_while_previous_chunk_is_still_playing():
    voice = _TrackingVoice()
    sink = _BlockingSink()

    assert_second_synth_completes_while_first_play_blocks(PiperTTS(voice=voice), voice, sink)


def test_each_text_is_yielded_only_after_its_audio_has_been_played():
    voice = _TrackingVoice()
    sink = _ImmediateSink()
    tts = PiperTTS(voice=voice)

    spoken = list(tts.speak_stream(_two_long_sentences(), sink))

    assert spoken == ["first long enough sentence", "second long enough sentence"]


def test_voice_synth_failure_surfaces_as_tts_error():
    tts = PiperTTS(voice=_ExplodingVoice())

    with pytest.raises(TTSError):
        list(tts.speak_stream(iter(["something long enough"]), _ImmediateSink()))


def test_sink_play_failure_surfaces_as_tts_error():
    tts = PiperTTS(voice=_TrackingVoice())

    with pytest.raises(TTSError):
        list(tts.speak_stream(iter(["something long enough"]), _ExplodingSink()))


def _angry_source():
    yield "first sentence is fine"
    raise _Boom()


def test_source_iterator_errors_propagate_unchanged_so_callers_can_distinguish_them():
    tts = PiperTTS(voice=_TrackingVoice())

    with pytest.raises(_Boom):
        list(tts.speak_stream(_angry_source(), _ImmediateSink()))


class _RecordingSink:
    def __init__(self, log: list[str]):
        self._log = log

    def play(self, pcm: bytes) -> None:
        self._log.append("play")


def _record_speak_events(texts) -> list[str]:
    events: list[str] = []
    list(PiperTTS(voice=_TrackingVoice()).speak_stream(
        texts, _RecordingSink(events),
        on_first_audio=lambda: events.append("first-audio"),
    ))
    return events


def test_on_first_audio_callback_fires_exactly_once_just_before_the_first_play():
    events = _record_speak_events(_two_long_sentences())

    assert events == ["first-audio", "play", "play"]


def test_on_first_audio_callback_is_not_invoked_when_no_audio_is_produced():
    events = _record_speak_events(iter([]))

    assert events == []
