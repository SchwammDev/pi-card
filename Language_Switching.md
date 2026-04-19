# Language Switching

The assistant can switch between supported languages mid-session via voice command. Switches are session-only — the configured default applies again after restart.

## Trigger Phrases

Recognized after STT by deterministic match (not interpreted by the AI):

| Current language | Phrases | Switch to |
|------------------|---------|-----------|
| English | "switch to French", "speak French" | French |
| French  | "passe en anglais", "parle anglais" | English |

## Behavior

1. STT runs in the current language and returns the utterance.
2. If the utterance matches a trigger phrase, the language flips before the next turn.
3. The assistant speaks a short acknowledgement in the new language (e.g., "D'accord, je parle français maintenant.").
4. The conversation continues; subsequent STT, AI replies, and TTS use the new language.

## Out of Scope (v1)

- Auto language detection from audio.
- Persistence across restarts (would mutate `config.yaml`).
- Mixed-language turns within a single utterance.
