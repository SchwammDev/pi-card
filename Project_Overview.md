# Raspberry Pi AI Voice Assistant

Lightweight voice assistant that runs on a Raspberry Pi 4+. Listens for a wake word, transcribes user speech, dispatches to an AI agent, and speaks the response.

## Supported Languages

- English
- French

The active language can be switched mid-session via voice command. See `Language_Switching.md`.

## Tech Stack

- **Language:** Python
- **Wake word detection:** openWakeWord, wake word "Computer" (offline, swappable to Porcupine if accuracy needs arise)
- **Speech-to-text:** Faster-Whisper, `base` model with `int8` compute type (offline, multilingual — user specifies language)
- **Text-to-speech:** Piper, voices `en_GB-alan-medium` (EN) and `fr_FR-siwis-medium` (FR) (offline, fast on Pi 4; swappable to cloud TTS later)
- **AI agent:** OpenAI-compatible API (user-configurable provider — see "AI Agent" below)

## Hardware & Audio

- **Audio input** — ReSpeaker 4-Mic HAT (I2S)
- **Audio output** — USB speakers
- **Abstraction** — Production code depends on abstract interfaces (Python ABCs), never on concrete hardware directly. Dependencies are injected via constructors. See `Hardware_Interfaces.md` for details.

## AI Agent

- **Interface** — accepts a list of messages (OpenAI chat-completions shape: `[{"role": ..., "content": ...}, ...]`) and returns a single assistant message.
- **System prompt** — "You are a concise voice assistant. Reply in 1–3 sentences unless asked for detail. Avoid markdown, lists, or code — your output is spoken aloud."
- **Model choice** — prefer non-reasoning models (e.g. `gpt-4o-mini`-class). Reasoning/thinking-mode models add hundreds of milliseconds to seconds of hidden chain-of-thought per reply — acceptable for chat, prohibitive for conversation. If using a reasoning-capable model, set the provider's `reasoning_effort`/`thinking`-equivalent to its minimum. v1 does not plumb this through — if a future deployment needs a reasoning-capable model, add a `reasoning_effort` field to `Config` and pass it through `OpenAIAgent.chat`.
- **History within a conversation** — full message history retained until silence timeout or explicit exit, then cleared.
- **History across conversations** — none in v1. The interface is shaped to allow a `MemoryStore` to be added later without changing call sites.

## Runtime Behavior

- **Conversation mode** — Multi-turn. After each response, the mic stays open for follow-ups. Conversation ends on silence timeout (default: 8s, configurable) or explicit exit ("goodbye", "that's all"), returning to wake-word mode.
- **Concurrency model** — v1: sequential pipeline (listen → transcribe → query → speak). v2 (deferred): stream AI response into TTS in sentence-sized chunks for lower perceived latency.
- **Error handling & feedback:**
  - **Network / API failure** — Play spoken error cue ("I can't reach my brain right now"), flash LED red, return to wake-word mode. No silent retries.
  - **Low-confidence STT** — Ask "Sorry, could you repeat that?" and re-listen. Max retries configurable (default: 2), then audio error cue + red LED, return to wake-word mode.
  - **TTS failure** — Play generic error tone, log error, return to wake-word mode.
  - **Audio hardware issues** — Detect on startup, fail fast with clear log message. LED solid red if available.
  - **LED feedback** — ReSpeaker HAT LEDs: pulsing blue = listening, pulsing green = thinking/processing, red flash = error.
  - **Logging** — Local error log with rotation for debugging.

## Privacy & Logging

- **Error log** — `~/.local/state/pi-card/logs/errors.log`. Always on.
- **Conversation transcripts** — off by default. Enabled with `--debug-transcripts`, written to `~/.local/state/pi-card/logs/transcripts.log`.
- **Audio retention** — never. Mic captures are processed in memory and discarded.
- **Rotation** — Python `RotatingFileHandler`, 1 MB per file, keep last 5 (~5 MB cap per log).
- **Format** — `%(asctime)s %(levelname)s %(name)s: %(message)s`.

## Testing Strategy

- Behavior-Driven Development — tests describe expected behaviors, not implementation.
- Plain pytest — no BDD framework. Well-named tests and domain-specific helper functions serve as the DSL.
- Acceptance tests organized by feature (conversation flow, wake word, STT, TTS, AI agent, error handling, configuration).
- Hardware dependencies (mic, speaker, LEDs, API) are faked via pytest fixtures. Fakes implement the hardware ABCs and are injected through constructors.

## Development Setup

- **Package manager:** uv (`pyproject.toml` + `uv.lock` committed)
- **Python:** 3.11+
- **Run tests:** `./run-tests.sh` (accepts usual `pytest` args, e.g. `./run-tests.sh -k "smoke"`)

### Repository Layout

```
pi-card/
├── pyproject.toml, uv.lock, Makefile
├── config.yaml.example
├── *.md                     # design docs at root
├── src/pi_card/
│   ├── __main__.py, cli.py, config.py
│   ├── assistant.py         # top-level orchestrator
│   ├── conversation.py      # turn state, language switching
│   ├── hardware/            # the four ABCs (see Hardware_Interfaces.md)
│   ├── adapters/            # production implementations
│   └── pipeline/            # wake-word, STT, TTS wrappers
└── tests/
    ├── conftest.py
    ├── dsl/                 # actions and assertions (see Acceptance_Test_Rules.md)
    ├── fakes/               # one fake per ABC
    └── features/            # acceptance tests, one file per feature area
```

`src/` layout is used to avoid local-directory import shadowing. Fakes live under `tests/` because they are test-only code.

## User-Facing Setup

- **Configuration** — Convention over Configuration. Single `config.yaml` with sensible defaults baked into code; file only needs overrides. Precedence: CLI args > config file > defaults.
  - **Defaults** — language: `en`, silence timeout: 8s, max STT retries: 2.
  - **Required (no default)** — `base_url`, `api_key`, `model` for the AI agent. Fail fast with clear message if unset.
  - **CLI overrides** — `--language`, `--log-level`, `--config` (alternate config path), `--debug-transcripts`. Only flags useful for dev/debugging.
- **Installation & deployment** — Makefile. Targets: `install` (venv + deps + default config), `run`, `service` (systemd auto-start), `uninstall`, `clean`. Assumes ReSpeaker HAT is already configured.

