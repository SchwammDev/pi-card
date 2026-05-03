import pytest

from pi_card.pipeline.stt import WhisperSTT
from tests.fakes.whisper_model import FakeWhisperModel


def _silent_pcm(seconds: float, sample_rate: int = 16_000) -> bytes:
    return b"\x00\x00" * int(seconds * sample_rate)


def test_transcribes_audio_in_the_requested_language():
    model = FakeWhisperModel({"en": "hello world"})
    stt = WhisperSTT(model=model)

    text = stt.transcribe(_silent_pcm(1.0), language="en")

    assert text == "hello world"


def test_forwards_the_requested_language_to_the_model():
    model = FakeWhisperModel({"fr": "bonjour"})
    stt = WhisperSTT(model=model)

    stt.transcribe(_silent_pcm(1.0), language="fr")

    assert model.calls[-1]["language"] == "fr"


def test_supports_switching_language_between_calls():
    model = FakeWhisperModel({"en": "good morning", "fr": "bonjour"})
    stt = WhisperSTT(model=model)

    first = stt.transcribe(_silent_pcm(1.0), language="en")
    second = stt.transcribe(_silent_pcm(1.0), language="fr")

    assert first == "good morning"
    assert second == "bonjour"
    assert [c["language"] for c in model.calls] == ["en", "fr"]


def test_passes_one_float_sample_per_pcm_frame():
    model = FakeWhisperModel({"en": ""})
    stt = WhisperSTT(model=model)

    stt.transcribe(_silent_pcm(0.5), language="en")

    assert model.calls[-1]["num_samples"] == int(0.5 * 16_000)


def test_returns_trimmed_text_when_model_pads_whitespace():
    model = FakeWhisperModel({"en": "   hello   "})
    stt = WhisperSTT(model=model)

    assert stt.transcribe(_silent_pcm(0.2), language="en") == "hello"


def test_rejects_pcm_with_odd_byte_length():
    model = FakeWhisperModel({"en": ""})
    stt = WhisperSTT(model=model)

    with pytest.raises(ValueError):
        stt.transcribe(b"\x00\x00\x00", language="en")


def test_enables_vad_filter_to_drop_non_speech_segments():
    model = FakeWhisperModel({"en": ""})
    stt = WhisperSTT(model=model)

    stt.transcribe(_silent_pcm(1.0), language="en")

    assert model.calls[-1]["kwargs"].get("vad_filter") is True


def test_disables_conditioning_on_previous_text_to_avoid_self_reinforcing_hallucinations():
    model = FakeWhisperModel({"en": ""})
    stt = WhisperSTT(model=model)

    stt.transcribe(_silent_pcm(1.0), language="en")

    assert model.calls[-1]["kwargs"].get("condition_on_previous_text") is False


def test_forwards_language_specific_initial_prompt_to_the_model():
    model = FakeWhisperModel({"en": ""})
    stt = WhisperSTT(model=model, initial_prompts={"en": "Voice assistant Q&A."})

    stt.transcribe(_silent_pcm(0.5), language="en")

    assert model.calls[-1]["kwargs"].get("initial_prompt") == "Voice assistant Q&A."


def test_uses_language_specific_prompt_for_each_language():
    prompts = {"en": "english prompt", "fr": "french prompt"}
    model, stt = _stt_with_prompts(prompts)

    _transcribe_short(stt, "en")
    _transcribe_short(stt, "fr")

    assert _prompts_seen(model) == ["english prompt", "french prompt"]


def _stt_with_prompts(prompts):
    model = FakeWhisperModel({lang: "" for lang in prompts})
    return model, WhisperSTT(model=model, initial_prompts=prompts)


def _transcribe_short(stt, language):
    stt.transcribe(_silent_pcm(0.5), language=language)


def _prompts_seen(model):
    return [c["kwargs"].get("initial_prompt") for c in model.calls]


def test_omits_initial_prompt_when_no_prompt_is_configured_for_language():
    model = FakeWhisperModel({"en": ""})
    stt = WhisperSTT(model=model)

    stt.transcribe(_silent_pcm(0.5), language="en")

    assert "initial_prompt" not in model.calls[-1]["kwargs"]
