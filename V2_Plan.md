# v2 Plan

## Status

First three items shipped. Two more added after a second listening test surfaced new bottlenecks (see "Forced into v2 by latency findings"): remote Aqueduct STT, then Piper first-synth. Sentence-chunker uses a minimum-viable splitter (terminal-punct + whitespace, 5-char floor) — accepted trade-off in `sentence_chunker.py`. Tighten only if real-Pi testing surfaces systematic mis-splits.

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

1. ~~**Keep LED at THINKING until first audio plays.**~~ Shipped. `PiperTTS.speak_stream` now takes an `on_first_audio` callback; `Conversation` wires it to flip the LED only when the first chunk's audio is about to play.
2. ~~**Lower sentence-chunker floor from 16 → 5 chars.**~~ Shipped. 5 still rejects "Mr." / "etc." but admits typical greetings. Accepted risk: occasional 4-char acronym (e.g. "U.S.") emits as a standalone chunk.
3. ~~**Verify Qwen `enable_thinking: false` is actually live in the deployed config.**~~ Confirmed. Logged at the SDK boundary on the Pi: `extra_body={'chat_template_kwargs': {'enable_thinking': False}}`. LLM TTFT measured at ~0.85 s, no chain-of-thought stall.

## Findings from second listening test

Instrumented THINKING with `pi_card.latency` markers. One real-Pi cycle, 5.4 s English prompt:

| span | duration | share |
|---|---|---|
| Whisper STT | 6.0 s | 65% |
| LLM TTFT | 0.85 s | 9% |
| chunker buffering | 0.22 s | 2% |
| Piper first synth | 2.14 s | 23% |

LLM is fine. STT and Piper-first-synth dominate.

Two hypotheses tested and dropped:

- **Piper ONNX cold-start.** Warmup at startup saved ~130 ms — within noise. Reverted. Piper medium is just genuinely ~real-time on Pi 4.
- **Streaming STT output via Aqueduct.** `whisper-large-v3-turbo` on `/audio/transcriptions` supports `stream=true`, but chat-completions can't accept a streaming user message — partial transcripts are unusable. Aqueduct does not expose `/realtime` (probed). Stick with non-streaming POST.

## Forced into v2 by latency findings

The original three v2 items shipped but didn't close the latency gap — second listening test still felt sluggish, instrumentation revealed STT and Piper-first-synth as the real bottlenecks. Two more items added to v2 to actually deliver the responsiveness goal:

4. **Swap STT to remote Aqueduct `whisper-large-v3-turbo`.** ~0.3 s wall-clock for a 5 s utterance — **~19× faster than local `base/int8`**. Privacy holds: Aqueduct is on-prem at TU Wien.
   - ~~New `AqueductWhisperSTT` adapter, same `transcribe(pcm, language) -> text` contract as the local one.~~ Shipped. Lives at `adapters/aqueduct_stt.py`; both adapters now satisfy a `SpeechToText` Protocol in `pipeline/stt.py`. Reuses the LLM `OpenAI` client (Aqueduct hosts both endpoints under the same `base_url` + `api_key`); wraps int16 PCM into an in-memory WAV before upload. No `prompt` field forwarded for now — `whisper-large-v3-turbo` shouldn't need the hallucination-prevention prompt the local `base/int8` did. Revisit if real-Pi testing surfaces hallucinations.
   - ~~Config gains `stt: { provider: local | aqueduct, model: whisper-large }`. Default `local` to preserve current behavior for users without Aqueduct access.~~ Shipped.
   - No fallback. Network failure surfaces via the existing network-error path (LLM call would fail next anyway).
5. **Cut Piper first-chunk synth.** Third listening test (below) confirmed the gap scales with first-sentence length, not cold start (0.6 s for "Four." vs 2.8 s for a long opening sentence). The chunker→first-audio gap *is* the synth time for sentence #1.
   - ~~**Streaming Piper.**~~ Ruled out by measurement — `scripts/measure_piper_chunks.py` on the Pi: 192-char sentence yielded **one** chunk after 4.21 s of synth (12.6 s of audio); 5-char sentence yielded **one** chunk after 0.18 s. Piper's VITS-based `synthesize()` is sentence-level — within one sentence the model does a single forward pass and yields one `AudioChunk` only when it's complete (`piper/voice.py:269-303`). No sub-sentence streaming exists in this architecture; the `b"".join(...)` in `tts.py:159` discards nothing.
   - **Useful side-finding: Piper runs at ~3× real-time on the Pi 4** (4.21 s synth → 12.6 s audio; 0.18 s → 0.48 s). Once the pipeline is full, gaps stay zero. The bottleneck is purely sentence #1.
   - ~~**Comma-split chunker for the first chunk only.**~~ Shipped (`pipeline/sentence_chunker.py`). When `first_chunk_pending` is true, splits also accept `,` + whitespace (still respecting the 5-char floor); flips off after the first emit so subsequent prosody stays natural. Cycle-2 listening test win: −1.36 s on a coffee-recipe opening with an early comma. No effect on no-comma openings (cycle 1, response-dependent) or on already-short openings (cycle 3).
   - ~~**Aqueduct hosted TTS (Kokoro).**~~ Tested, not pursued. Aqueduct exposes `kokoro` (EN) and `piper-thorsen` (DE only — useless for our EN+FR). Kokoro probe (`scripts/probe_aqueduct_tts.py`): 3.59–3.75 s TTFB for a 192-char sentence, 0.43–0.46 s for "Four." — same ~3× real-time ratio as local Piper, with TTFB ≈ total wall on every call (server is non-streaming regardless of `response_format=wav` or `pcm`). Net: marginal gain on long sentences, regression on short ones, plus network dependency. Fidelity roughly comparable to local Piper. Lane re-opens only if TU Wien enables a streaming server.
   - **Status: partial ship.** Comma-split is in. Cycle-1 no-comma case still hits ~3 s of Piper synth — not closed. The architectural cap is that VITS-style models do one forward pass per sentence; the only way to start audio sooner without comma-split is to swap to a TTS architecture that streams audio progressively during decoding. **Investigation is the remaining half of this item** — see "Streaming TTS investigation" below.

Projected THINKING budget after item 4: **~3.5 s** (down from 9.3 s). Item 5 trims further from there.

## Findings from third listening test (after item 4)

Three cycles on the Pi against Aqueduct `whisper-large-v3-turbo` + `qwen-3.6-35b`:

| cycle | utterance | stt_done | LLM TTFT | chunker→first audio (Piper) | THINKING total |
|---|---|---|---|---|---|
| 1 | long story prompt | 1.07 s | +0.20 s | +2.80 s | **4.28 s** |
| 2 | medium prompt | 0.31 s | +0.24 s | +2.12 s | **2.91 s** |
| 3 | "two plus two" | 0.26 s | +0.19 s | +0.60 s | **1.14 s** |

- **STT goal hit** for typical utterances: 0.26–0.31 s, matching the ~19× projection. Cycle 1's 1.07 s scales with audio length (and may include first-call TLS handshake) — not worth chasing yet.
- **Projection beaten on cycles 2 and 3** (2.9 s and 1.1 s vs projected ~3.5 s). Cycle 1 misses because of Piper, not Whisper.
- **Piper first-chunk synth is the only remaining bottleneck.** The chunker→first-audio gap scales with first-chunk text length (0.6 s for a short greeting, ~2.8 s for a long opening sentence). Earlier "warmup saved only ~130 ms" finding still holds — what we're seeing now isn't cold start, it's synth time tracking sentence length.

This reframes item 5: the leverage is on **shortening the first chunk**, not on warming Piper or finding a streaming API.

## Streaming TTS investigation (remainder of item 5)

Comma-split shipped, but the cycle-1 no-comma case still hits ~3 s of Piper synth before first audio. The architectural cap is **VITS-style models do one forward pass per sentence** — the only way to start audio sooner is either (a) shorten the input passed to one synth call (comma-split, already shipped) or (b) swap to a TTS architecture that streams audio progressively during decoding.

Candidates worth probing in a follow-up investigation:

- **XTTS-v2 (Coqui).** Exposes a documented streaming inference API (`tts.tts_stream(...)`) yielding audio chunks during decoding. Larger model — needs verification whether it runs usefully on Pi 4 CPU or whether self-hosting on a faster machine is required.
- **Streaming-VITS forks.** Research forks (e.g., chunked-decoder VITS variants) that yield audio progressively. Untested on Pi, mainline status unclear.
- **Self-hosted Kokoro with a streaming front-end.** Kokoro itself isn't streaming, but a thin server wrapper that decomposes input by sentence and writes the response with `Transfer-Encoding: chunked` would enable network-side streaming. Server complexity, but reuses a model whose fidelity we've already heard.
- **OpenAI Realtime / gpt-realtime / Gemini Live.** End-to-end audio. Out of scope until TU Wien hosts an audio-capable LLM behind Aqueduct (privacy constraint).

Pre-investigation step before any code: measurement, same approach as the Piper chunk and Aqueduct probes — survey what's available, time TTFA on the Pi or representative hardware, listen for fidelity. Decide architecture only after numbers.

## Out of scope for v2

- Cross-conversation memory (deferred per `Project_Overview.md`).
