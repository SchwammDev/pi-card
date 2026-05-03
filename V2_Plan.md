# v2 Plan

## What v1 hardware testing taught us

- **Energy-RMS VAD is fundamentally limited.** It cannot distinguish a 2-frame "yes" from a 2-frame noise burst — they look identical. Tuning `pause_tolerance` / `speech_rms_threshold` only shifts which mistakes happen.
- **Whisper hallucinates from near-silent audio**, especially with a dialog-biased `initial_prompt`. Caught once in real use: the assistant produced a fake multi-turn transcript out of ambient noise.
- **Sequential pipeline feels sluggish.** Full LLM completion before TTS dominates perceived latency (already documented in `Project_Overview.md`).

## What v2 must do

1. **Replace energy VAD with silero-vad.** Solves false endpointing (deliberate-thinking pauses no longer cut off) and noise-as-utterance (silero won't commit ambient noise). Drops `speech_rms_threshold`; renames `pause_tolerance` → `min_silence_duration_ms` (silero's vocabulary, int ms, end-to-end single unit).
2. **Stream LLM output into TTS in sentence-sized chunks.** First spoken word arrives much sooner; users stop perceiving sluggishness.

Order: **silero-vad first** (UX-blocking — device is hard to use without it), **streaming second** (performance polish).

### Design decisions for silero-vad replacement

- **Dependency:** `onnxruntime` directly, not the `silero-vad` PyPI package — the latter pulls full torch + CUDA wheels (~3 GB), unusable on a Pi 4. `onnxruntime` is ~50 MB with an aarch64 manylinux wheel.
- **Model file:** `silero_vad.onnx` (2.3 MB) downloaded on first use by the loader, mirroring `load_piper_voice`. Cached under `~/.local/share/pi-card/`. Not committed to the repo, not fetched at install time.
- **Interface:** new `SpeechDetector` ABC with `is_speech(frame) -> bool` and `reset()`. Production wires `SileroSpeechDetector` (wraps an `onnxruntime.InferenceSession`); tests wire a scripted fake.
- **State machine stays:** `capture_utterance`'s start-debounce / preroll / trailing-silence / max-duration logic is preserved. Only `_is_speech` is replaced; the detector is injected.
- **Frame-size bridging:** audio frames are 1280 samples (80 ms), silero wants 512 samples (32 ms) — non-integer ratio. `SileroSpeechDetector` buffers samples internally, drains full 512-sample windows per call, aggregates per-window probabilities into one bool, holds the remainder for the next call. `reset()` flushes between utterances.

## Out of scope for v2

- Cross-conversation memory (deferred per `Project_Overview.md`).
- `reasoning_effort` plumbing (deferred — add only when a deployment needs it).
