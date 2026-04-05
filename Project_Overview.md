# Raspberry Pi AI Voice Assistant

Lightweight voice assistant that runs on a Raspberry Pi 4+. Listens for a wake word, transcribes user speech, dispatches to an AI agent, and speaks the response.

## Supported Languages

- English
- French

## Tech Stack

- **Language:** Python
- **Wake word detection:** openWakeWord (offline, swappable to Porcupine if accuracy needs arise)
- **Speech-to-text:** Faster-Whisper (offline, multilingual — user specifies language)
- **Text-to-speech:** Piper (offline, fast on Pi 4; swappable to cloud TTS later)
- **AI agent:** OpenAI-compatible API (user-configurable provider)

## Hardware & Audio

- **Audio input** — ReSpeaker 4-Mic HAT (I2S)
- **Audio output** — USB speakers
- **Abstraction** — Production code depends on abstract interfaces (Python ABCs), never on concrete hardware directly. Dependencies are injected via constructors. See `Hardware_Interfaces.md` for details.

## Runtime Behavior

- **Conversation mode** — Multi-turn. After each response, the mic stays open for follow-ups. Conversation ends on silence timeout (default: 8s, configurable) or explicit exit ("goodbye", "that's all"), returning to wake-word mode.
- **Concurrency model** — Sequential pipeline (listen → transcribe → query → speak) to start. Later, stream AI response into TTS in sentence-sized chunks for lower perceived latency.
- **Error handling & feedback:**
  - **Network / API failure** — Play spoken error cue ("I can't reach my brain right now"), flash LED red, return to wake-word mode. No silent retries.
  - **Low-confidence STT** — Ask "Sorry, could you repeat that?" and re-listen. Max retries configurable (default: 2), then audio error cue + red LED, return to wake-word mode.
  - **TTS failure** — Play generic error tone, log error, return to wake-word mode.
  - **Audio hardware issues** — Detect on startup, fail fast with clear log message. LED solid red if available.
  - **LED feedback** — ReSpeaker HAT LEDs: pulsing blue = listening, pulsing green = thinking/processing, red flash = error.
  - **Logging** — Local error log with rotation for debugging.

## Testing Strategy

- Behavior-Driven Development — tests describe expected behaviors, not implementation.
- Plain pytest — no BDD framework. Well-named tests and domain-specific helper functions serve as the DSL.
- Acceptance tests organized by feature (conversation flow, wake word, STT, TTS, AI agent, error handling, configuration).
- Hardware dependencies (mic, speaker, LEDs, API) are faked via pytest fixtures. Fakes implement the hardware ABCs and are injected through constructors.

## Development Setup

- **Package manager:** uv (`pyproject.toml` + `uv.lock` committed)
- **Python:** 3.11+
- **Run tests:** `uv run pytest`

## User-Facing Setup

- **Configuration** — Convention over Configuration. Single `config.yaml` with sensible defaults baked into code; file only needs overrides. Precedence: CLI args > config file > defaults.
  - **Defaults** — language: `en`, silence timeout: 8s, max STT retries: 2.
  - **Required (no default)** — API provider, API key. Fail fast with clear message if unset.
  - **CLI overrides** — `--language`, `--log-level`, `--config` (alternate config path). Only flags useful for dev/debugging.
- **Installation & deployment** — Makefile. Targets: `install` (venv + deps + default config), `run`, `service` (systemd auto-start), `uninstall`, `clean`. Assumes ReSpeaker HAT is already configured.

