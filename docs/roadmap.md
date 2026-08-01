# Roadmap

Planning lives on GitHub: [milestones](https://github.com/SchwammDev/pi-card/milestones) hold the stages, issues hold the user stories (requirements + broad direction). Rolling main release — no versions.

Delivery sequence:

1. **Tool Use Foundation** — dispatch loop, time/date, timers, Notifier
2. **Nextcloud: Read Access** — "what do I have to do today"; includes the pydantic-ai substrate spike
3. **Reminders** — persistent, survive restart
4. **Nextcloud: Write & Planning** — dictate notes, calendar writes, plan my day/week
5. **Barge-in** — interrupt mid-reply; announcements cut in
6. **Conversation Memory** — cross-session, opt-in

Sequencing rationale: the tool loop hardens the streaming path before real tools land on it; Nextcloud read and reminders deliver value before conversation polish (barge-in); memory pays off only once tools generate state worth remembering.

Substrate decision (recorded 2026-05): Python-native. Before the first Nextcloud tool, a spike validates pydantic-ai as the dispatcher substrate; the handrolled loop ships first for Tool Use Foundation. A pi-harness sidecar was considered and rejected — convergence was not valued over right-tool-for-the-job.

## Shipped

| Version | Theme |
|---|---|
| v1.1.1 | Hallucinated-transcript gate (low `avg_logprob` → silent skip), 2026-05-12 — local Faster-Whisper only; Aqueduct returns null confidence, gate dormant there |

## Not pursuing

- Third-party cloud STT — ruled out by privacy posture; Aqueduct covers the speed case.
- Web or mobile UI — the device is the interface.
- Multi-device sync — no second device.
