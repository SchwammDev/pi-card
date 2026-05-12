# Developing pi-card

Practical doc for working on the codebase. Product/design spec lives in [`Project_Overview.md`](Project_Overview.md).

## Workflow

- Python 3.11+, `uv` (committed `pyproject.toml` + `uv.lock`).
- Run tests: `./run-tests.sh` (forwards args to pytest, e.g. `./run-tests.sh -k smoke`).
- Pre-commit hooks block Python comments and docstrings, and flag long tests. Code communicates through names; hide setup and assertions behind intent-named helpers.

## Test conventions

- Plain pytest, no BDD framework. Test names describe observable contracts (`test_first_sentence_is_spoken_before_the_agent_stream_completes`).
- Acceptance tests in `tests/features/`, organised by feature area. They drive a `World` of fakes through a small DSL.
- DSL in `tests/dsl/` — `actions.py` for arrange/act helpers, `assertions.py` for intent-named asserts.
- Fakes in `tests/fakes/`, one per ABC, injected via the `world` fixture in `conftest.py`.
- TDD: write the test first, observe it fail for the right reason, then implement.

## Pi listening test protocol

After any change to STT, agent streaming, sentence chunker, or TTS pipeline, run these on a real Pi. Each is one wake → prompt → listen → "goodbye" cycle.

| # | Prompt | Listen for |
|---|---|---|
| 1 | "Tell me a short story about a robot learning to garden." | First-word latency. Speech should start well before the LLM could plausibly have finished. |
| 2 | "Describe what makes a good cup of coffee in three sentences." | Inter-chunk gaps; sentence boundaries make sense — no mid-word cuts, no abbreviation fragments. |
| 3 | "What is two plus two?" | Short single-sentence reply still speaks (chunker's end-flush path). |

## Extension points

Production code depends on ABCs, never on concrete hardware. Each boundary has a production implementation and a test fake.

| ABC | Production | Test Fake | Responsibility |
|-----|------------|-----------|----------------|
| `AudioInput` | ReSpeaker 4-Mic HAT | Returns pre-recorded audio bytes | Mic capture |
| `AudioOutput` | USB speakers | Records played PCM | Speaker playback |
| `LEDController` | ReSpeaker HAT LEDs | Records state changes | LED feedback |
| `AIAgent` | OpenAI-compatible client | Yields canned text deltas | LLM streaming |

**Audio format** (uniform across `AudioInput`/`AudioOutput` to avoid resampling): 16 kHz, mono, 16-bit signed PCM, little-endian. Input frame size: 1280 samples (80 ms) — openWakeWord's native chunk.

**Injection:** constructor injection, no DI framework. Tests wire fakes through the same constructor — see `tests/conftest.py`.

## Dependency notes

- **`tflite-runtime` source pin in `pyproject.toml`.** `[tool.uv.sources]` redirects `tflite-runtime` to PyPI. `tflite-runtime` is a transitive dep of `openwakeword`, and `openwakeword` itself resolves from a private index (`git.eodc.eu`) that does not host `tflite-runtime`. Without the override, lock resolution fails. Looks dead because the package isn't in `dependencies`, but removing it breaks `uv lock` on a clean checkout. Leave it.
