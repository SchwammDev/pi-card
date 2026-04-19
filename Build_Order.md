# Build Order

Sequential phases for building v1. Each phase produces something runnable or testable; later phases depend on earlier ones. Delete this file once v1 ships.

## Phase 1 — Skeleton and contracts

- `pyproject.toml`, package layout under `src/pi_card/`
- The four hardware ABCs in `src/pi_card/hardware/` (`AudioInput`, `AudioOutput`, `LEDController`, `AIAgent`)
- Test scaffolding: `tests/conftest.py`, `tests/dsl/` (actions + assertions), `tests/fakes/` (one fake per ABC)
- Config loader (`config.py`) with required-field validation

**Done when:** `uv run pytest` runs green on a trivial smoke test that wires fakes through an empty orchestrator.

## Phase 2 — Pipeline wrappers (against fakes)

- `pipeline/wake_word.py` — openWakeWord wrapper consuming `AudioInput`
- `pipeline/stt.py` — Faster-Whisper wrapper (base, int8) consuming `AudioInput`
- `pipeline/tts.py` — Piper wrapper producing frames for `AudioOutput`

**Done when:** acceptance tests for wake-word, STT, and TTS pass against fakes.

## Phase 3 — Orchestrator

- `assistant.py` — top-level wiring
- `conversation.py` — turn state, in-conversation history, silence timeout, exit phrases
- Language switching (deterministic trigger-phrase match, ack in new language)
- Error handling and LED feedback per the spec

**Done when:** all acceptance tests in `tests/features/` pass against fakes.

## Phase 4 — Production hardware adapters (parallel-friendly)

These four are independent and tested against the same fakes/contracts from Phase 1. Build in parallel if convenient:

- `adapters/respeaker_input.py`
- `adapters/respeaker_leds.py`
- `adapters/usb_speaker.py`
- `adapters/openai_agent.py`

**Done when:** the assistant runs end-to-end on a Pi with real hardware.

## Phase 5 — Packaging

- `cli.py` and `__main__.py` with the documented flags
- `Makefile` targets: `install`, `run`, `service`, `uninstall`, `clean`
- systemd unit for auto-start
- `config.yaml.example` with all defaults documented

**Done when:** `make install && make service` brings the assistant up on a fresh Pi.

## Out of Scope for v1

- Streaming TTS (deferred to v2; see `Project_Overview.md`)
- Cross-conversation memory (interface seam exists; no implementation)
- Auto language detection
