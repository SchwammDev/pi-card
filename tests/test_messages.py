import pytest

from pi_card.messages import (
    SUPPORTED_LANGUAGES,
    detect_language_switch,
    is_exit_phrase,
    network_error_cue,
    normalize,
    switch_acknowledgement,
)


class TestNormalize:
    def test_lowercases_text(self):
        assert normalize("Goodbye") == "goodbye"

    def test_strips_surrounding_whitespace(self):
        assert normalize("   hello   ") == "hello"

    @pytest.mark.parametrize("suffix", [".", "!", "?", ","])
    def test_strips_trailing_punctuation(self, suffix):
        assert normalize(f"goodbye{suffix}") == "goodbye"

    def test_strips_trailing_punctuation_stack(self):
        assert normalize("goodbye?!") == "goodbye"

    def test_preserves_inner_punctuation(self):
        assert normalize("that's all.") == "that's all"


class TestIsExitPhrase:
    @pytest.mark.parametrize("phrase", ["goodbye", "good bye", "bye", "that's all"])
    def test_recognises_english_exit_phrases(self, phrase):
        assert is_exit_phrase(phrase, language="en")

    @pytest.mark.parametrize("phrase", ["Good bye!", "Bye.", "good bye now"])
    def test_recognises_whisper_variants_of_goodbye(self, phrase):
        assert is_exit_phrase(phrase, language="en")

    @pytest.mark.parametrize("phrase", ["au revoir", "c'est tout"])
    def test_recognises_french_exit_phrases(self, phrase):
        assert is_exit_phrase(phrase, language="fr")

    def test_rejects_non_exit_phrases(self):
        assert not is_exit_phrase("what's the weather", language="en")

    def test_matches_after_normalisation(self):
        assert is_exit_phrase("Goodbye.", language="en")

    def test_does_not_cross_language_boundaries(self):
        assert not is_exit_phrase("au revoir", language="en")
        assert not is_exit_phrase("goodbye", language="fr")

    def test_triggers_when_exit_phrase_is_embedded_in_a_longer_utterance(self):
        assert is_exit_phrase("okay, goodbye", language="en")
        assert is_exit_phrase("alright that's all for now", language="en")


class TestDetectLanguageSwitch:
    @pytest.mark.parametrize("phrase", ["switch to french", "speak french"])
    def test_english_switches_to_french(self, phrase):
        assert detect_language_switch(phrase, current_language="en") == "fr"

    @pytest.mark.parametrize("phrase", ["passe en anglais", "parle anglais"])
    def test_french_switches_to_english(self, phrase):
        assert detect_language_switch(phrase, current_language="fr") == "en"

    def test_returns_none_when_no_trigger_matches(self):
        assert detect_language_switch("what's the weather", current_language="en") is None

    def test_normalises_before_matching(self):
        assert detect_language_switch("Switch to French!", current_language="en") == "fr"

    def test_ignores_triggers_meant_for_other_current_language(self):
        # An English trigger shouldn't fire when the current language is French.
        assert detect_language_switch("switch to french", current_language="fr") is None

    def test_triggers_when_switch_phrase_is_embedded_in_a_longer_utterance(self):
        assert detect_language_switch("and switch to french", current_language="en") == "fr"
        assert detect_language_switch("please speak french now", current_language="en") == "fr"


class TestSwitchAcknowledgement:
    def test_french_ack(self):
        assert switch_acknowledgement(language="fr") == "D'accord, je parle français maintenant."

    def test_english_ack(self):
        assert switch_acknowledgement(language="en") == "Okay, I'll speak English now."


class TestNetworkErrorCue:
    def test_english_cue(self):
        assert network_error_cue(language="en") == "I can't reach my brain right now."

    def test_french_cue(self):
        assert (
            network_error_cue(language="fr")
            == "Je n'arrive pas à joindre mon cerveau pour le moment."
        )


def test_supported_languages_are_en_and_fr():
    assert SUPPORTED_LANGUAGES == ("en", "fr")
