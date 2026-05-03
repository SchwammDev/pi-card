# v2 Plan

## What v1 hardware testing taught us

- **Energy-RMS VAD is fundamentally limited.** It cannot distinguish a 2-frame "yes" from a 2-frame noise burst — they look identical. Tuning `pause_tolerance` / `speech_rms_threshold` only shifts which mistakes happen.
- **Whisper hallucinates from near-silent audio**, especially with a dialog-biased `initial_prompt`. Caught once in real use: the assistant produced a fake multi-turn transcript out of ambient noise.
- **Sequential pipeline feels sluggish.** Full LLM completion before TTS dominates perceived latency (already documented in `Project_Overview.md`).

## What v2 must do

1. **Replace energy VAD with silero-vad.** Solves false endpointing (deliberate-thinking pauses no longer cut off) and noise-as-utterance (silero won't commit ambient noise). Obsoletes `pause_tolerance` and `speech_rms_threshold` config knobs — plan their removal/repurposing as part of the change.
2. **Stream LLM output into TTS in sentence-sized chunks.** First spoken word arrives much sooner; users stop perceiving sluggishness.

Order: **silero-vad first** (UX-blocking — device is hard to use without it), **streaming second** (performance polish).

## Out of scope for v2

- Cross-conversation memory (deferred per `Project_Overview.md`).
- `reasoning_effort` plumbing (deferred — add only when a deployment needs it).
