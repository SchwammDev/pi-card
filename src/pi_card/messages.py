from dataclasses import dataclass

SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "fr")

_TRAILING_PUNCTUATION = ".!?,"


def normalize(text: str) -> str:
    """Lowercase, strip surrounding whitespace, and trim trailing .!?, characters."""
    return text.strip().lower().rstrip(_TRAILING_PUNCTUATION).strip()


@dataclass(frozen=True)
class _LanguageMessages:
    exit_phrases: tuple[str, ...]
    switch_triggers: dict[str, tuple[str, ...]]
    switch_ack: str
    network_error_cue: str
    repeat_prompt: str


_MESSAGES: dict[str, _LanguageMessages] = {
    "en": _LanguageMessages(
        exit_phrases=("goodbye", "that's all"),
        switch_triggers={"fr": ("switch to french", "speak french")},
        switch_ack="Okay, I'll speak English now.",
        network_error_cue="I can't reach my brain right now.",
        repeat_prompt="Sorry, could you repeat that?",
    ),
    "fr": _LanguageMessages(
        exit_phrases=("au revoir", "c'est tout"),
        switch_triggers={"en": ("passe en anglais", "parle anglais")},
        switch_ack="D'accord, je parle français maintenant.",
        network_error_cue="Je n'arrive pas à joindre mon cerveau pour le moment.",
        repeat_prompt="Désolé, pouvez-vous répéter ?",
    ),
}


def is_exit_phrase(text: str, *, language: str) -> bool:
    return normalize(text) in _MESSAGES[language].exit_phrases


def detect_language_switch(text: str, *, current_language: str) -> str | None:
    normalised = normalize(text)
    for target, phrases in _MESSAGES[current_language].switch_triggers.items():
        if normalised in phrases:
            return target
    return None


def switch_acknowledgement(*, language: str) -> str:
    return _MESSAGES[language].switch_ack


def network_error_cue(*, language: str) -> str:
    return _MESSAGES[language].network_error_cue


def repeat_prompt(*, language: str) -> str:
    return _MESSAGES[language].repeat_prompt
