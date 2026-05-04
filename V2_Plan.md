# v2 Plan

## Status

All three items shipped. Sentence-chunker uses a minimum-viable splitter (terminal-punct + whitespace, 16-char floor) — accepted trade-off in `sentence_chunker.py`. Tighten only if real-Pi testing surfaces systematic mis-splits.

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

## Forced into v2 by deployment reality

3. **Disable model "thinking" via `extra_body` passthrough.** Originally deferred, but every model now available to the target deployment (Qwen3 via Aqueduct/TU Wien) is thinking-capable, and chain-of-thought latency makes voice unusable. Implemented as an optional `extra_body: dict` config field, forwarded verbatim to the chat-completions request body. Generic passthrough rather than a `reasoning_effort` enum because providers disagree on vocabulary (OpenAI's `reasoning_effort`, Anthropic's `thinking`, Qwen's `enable_thinking`) — encoding any single one in `Config` would leak provider into the schema.

## Follow-ups from first Pi listening test

Streaming + pipelined synth shipped fine. New bottleneck: perceived gap between the THINKING LED and the first spoken word — TTFT plus chunker buffering plus first-chunk synth. Cheap wins:

1. **Keep LED at THINKING until first audio plays.** Today it flips OFF at the top of `_stream_reply_to_speech`, leaving the user with no feedback through the entire wait. Wire an `on_first_audio` callback into `PiperTTS.speak_stream` and move the LED transition there.
2. **Lower sentence-chunker floor from 16 → 5 chars.** Floor of 16 glues short opening sentences ("Hi there." waits for a longer follow-up). 5 still rejects "Mr." / "etc." but admits typical greetings. Accepted risk: occasional 4-char acronym (e.g. "U.S.") emits as a standalone chunk.
3. **Verify Qwen `enable_thinking: false` is actually live in the deployed config.** TTFT is model-bound; a thinking-on Qwen3 inflates it dramatically. Config check, not code.

## Out of scope for v2

- Cross-conversation memory (deferred per `Project_Overview.md`).
