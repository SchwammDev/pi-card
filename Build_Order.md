# Build Order

Sequential phases for building v1. Each phase produces something runnable or testable; later phases depend on earlier ones. Delete this file once v1 ships.

Manual-gate runbooks (scripts and shell commands) live in `Manual_Gates.md`. This file keeps the intent and pass criteria.

## Phase 1 — Skeleton and contracts ✅ complete

- `pyproject.toml`, package layout under `src/pi_card/`
- The four hardware ABCs in `src/pi_card/hardware/` (`AudioInput`, `AudioOutput`, `LEDController`, `AIAgent`)
- Test scaffolding: `tests/conftest.py`, `tests/dsl/` (actions + assertions), `tests/fakes/` (one fake per ABC)
- Config loader (`config.py`) with required-field validation

**Done when:** `uv run pytest` runs green on a trivial smoke test that wires fakes through an empty orchestrator.

## Phase 2 — Pipeline wrappers (against fakes) ✅ complete

- `pipeline/wake_word.py` — openWakeWord wrapper consuming `AudioInput`
- `pipeline/stt.py` — Faster-Whisper wrapper (base, int8) consuming `AudioInput`
- `pipeline/tts.py` — Piper wrapper producing frames for `AudioOutput`

**Done when:** acceptance tests for wake-word, STT, and TTS pass against fakes.

### Manual gate — TTS voice quality

Piper voice quality is subjective. Confirm now while voices are still cheap to swap.

- Validates the voice subjectively: intelligible, natural enough for an assistant, French accents/liaisons acceptable.
- Also validates a contract constraint: the TTS wrapper must emit frames as **16 kHz / mono / 16-bit PCM**.
- If voices aren't acceptable, pick a different one from the Piper samples gallery and update config. Don't defer this to Phase 4.

## Phase 3 — Orchestrator  ✅ complete

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

### Manual gate — per-adapter hardware bring-up

Each adapter needs a human in front of the Pi the first time. Where a Phase 2 wrapper already consumes the adapter, route through it — that exercises the seam between the adapter and the rest of the package, not just the hardware.

Pass criteria:

- **ReSpeaker input** (via `pipeline/stt.py`): transcript roughly matches what was spoken. Garbled output points at sample rate, channels, or mic gain.
- **USB speaker** (via `pipeline/tts.py`): audible at usable volume, no crackle, no buffer-underrun warnings in the log.
- **ReSpeaker LEDs**: pulsing blue → pulsing green → red flash, each visually distinct and matching the spec.
- **OpenAI agent**: sensible reply in under ~2 s. **Design budget:** 5+ s here means the full pipeline will feel sluggish — investigate before moving on.

### Manual gate — full conversation, ears only

With all four adapters wired in, run the assistant and have a real conversation. You're judging *felt* quality, which acceptance tests cannot.

Exercises to cover:

- Wake word + simple question/reply.
- Follow-up that depends on the previous turn (tests in-conversation history end-to-end).
- 8-second silence timeout returns to wake-word mode.
- "goodbye" mid-conversation triggers explicit exit.
- Trigger-phrase language switch: ack comes back in the new language, subsequent replies stay in it.
- Network unplugged: spoken error cue plays and LED flashes red.

Judge: does the multi-turn rhythm feel natural? Is end-to-end latency tolerable (wake → reply start)? Does the 8 s silence timeout feel right, or should the default change?

**Done when:** the assistant runs end-to-end on a Pi with real hardware and the manual conversation gate above passes.

## Phase 5 — Packaging

- `cli.py` and `__main__.py` with the documented flags
- `Makefile` targets: `install`, `run`, `service`, `uninstall`, `clean`
- systemd unit for auto-start
- `config.yaml.example` with all defaults documented

**Done when:** `make install && make service` brings the assistant up on a fresh Pi.

### Manual gate — fresh-Pi install

The only way to catch missing system deps, wrong paths, or systemd unit mistakes is to install on a Pi you haven't been developing on.

Pass criteria:

- `make install`: no errors, default config written, venv created.
- `make run` (after filling in `base_url`, `api_key`, `model`): assistant comes up, wake word works, one round-trip succeeds.
- `make service` + reboot: after boot, with no manual intervention, saying "Computer" gets a response.
- `journalctl -u pi-card` clean — anything noisy on a clean install is a packaging bug worth fixing now.
- `make uninstall`: service stopped and removed, no leftover files outside the repo.

## Out of Scope for v1

- Streaming TTS (deferred to v2; see `Project_Overview.md`)
- Cross-conversation memory (interface seam exists; no implementation)
- Auto language detection
