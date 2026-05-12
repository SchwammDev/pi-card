# Roadmap

| Version | Theme | Status |
|---|---|---|
| v1.1.1 | Hallucinated-transcript gate (low `avg_logprob` → silent skip) | shipped 2026-05-12 — local Faster-Whisper only; Aqueduct returns null confidence, gate dormant there |
| v1.2 | Tool use | designing — see [`features/tool-use.md`](features/tool-use.md) |
| v1.3 | Barge-in (VAD during playback + lane cancellation) | not started |
| v1.4+ | Conversation memory across sessions | not started |

Tool use first because it reshapes the streaming path; barge-in lands on the hardened version; memory only pays off once tools generate state worth remembering.

## Not pursuing

- Third-party cloud STT — ruled out by privacy posture; Aqueduct covers the speed case.
- Web or mobile UI — the device is the interface.
- Multi-device sync — no second device.
