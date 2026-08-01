# Roadmap

Planning lives on GitHub: [milestones](https://github.com/SchwammDev/pi-card/milestones) hold the stages, issues hold the user stories (requirements + broad direction). Rolling main release — no versions.

The vision is a growing personal-agent platform: an always-on **agent core** (Hetzner, co-located with Nextcloud) with thin channel frontends — pi-card is the voice frontend, Signal the text frontend. Proactive capabilities (scheduling, reminders, email triage) live in the core.

Delivery sequence:

1. **Tool Use Foundation** — voice-local dispatch loop, time/date, timers, Notifier
2. **Core Split** — substrate spike (pi-agent-core), core daemon on Hetzner, voice becomes thin client
3. **Nextcloud: Read Access** — "what do I have to do today"; tools live in the core
4. **Reminders** — persistent, survive restart
5. **Nextcloud: Write & Planning** — dictate notes, calendar writes, plan my day/week
6. **Text Channel** — Signal adapter behind a channel ABC; Matrix as fallback
7. **Proactive Autonomy** — commitment capture, self-scheduled reminders, email triage
8. **Barge-in** — interrupt mid-reply; announcements cut in
9. **Conversation Memory** — cross-session, opt-in, shared across channels

Sequencing rationale: the voice-local loop hardens the streaming path first; the Core Split lands before Nextcloud tools because tools live in the core; read and reminders deliver value before write/planning; Text Channel gives proactivity a way to reach the user on the road; barge-in is conversation polish, value comes first; memory pays off once tools generate state worth remembering — and multi-channel makes shared context load-bearing.

Substrate decision (recorded 2026-05): **pi-agent-core** (TypeScript) for the agent core, validated by a spike before the split. An earlier Python-native plan (pydantic-ai) was the right call for a standalone voice appliance; the platform vision made extensibility the deciding axis — pi's first-class extensions and agent self-extension, plus a trusted maintainer. pydantic-ai is the documented fallback if the spike fails. The voice frontend's audio pipeline stays Python regardless.

Privacy posture: audio stays on-device; transcripts transit to the Hetzner core (same trust domain as Nextcloud). Core unreachable → voice frontend degrades with the existing spoken-error pattern.

## Shipped

| Version | Theme |
|---|---|
| v1.1.1 | Hallucinated-transcript gate (low `avg_logprob` → silent skip), 2026-05-12 — local Faster-Whisper only; Aqueduct returns null confidence, gate dormant there |

## Not pursuing

- Third-party cloud STT — ruled out by privacy posture; Aqueduct covers the speed case.
- Multi-device sync — channels converge on the core instead.
