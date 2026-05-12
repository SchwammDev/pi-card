# v1.2 — Implementation plan

Phased rollout of [`tool-use.md`](tool-use.md). Each phase ends at a gate; do not start the next until it passes. Red-before-green throughout.

## Phase 1 — `StreamEvent` on `AIAgent`

Widen the return type only: `Iterator[str]` → `Iterator[StreamEvent]`, with `TextDelta` and `TurnDone` produced. OpenAI adapter, orchestrator, and `AIAgent` fake updated together. No new feature tests.

Gate: full test suite green.

## Phase 2 — `ToolDispatcher` passthrough

Insert `ToolDispatcher` between orchestrator and `AIAgent` with an empty `ToolRegistry`; dispatcher forwards `TextDelta.text` unchanged. New test asserts passthrough fidelity against a fake agent. Existing tests rewire through the dispatcher with no logic change.

Gate: full test suite green.

## Phase 3 — `current_time`, `current_date`

Adds `Clock` ABC, the two time-tool handlers, their registrations, and the dispatcher's tool loop. System prompt addendum and `max_tool_rounds` config plumbed.

Tests, `tests/features/tool_use.py`:
- Single-round tool: fake agent emits `ToolCall(current_time)` → `TurnDone(tool_calls)`; `Clock` fake fixed at a known instant; assertion on the spoken reply.
- Prelude path: text delta before the `ToolCall` reaches the chunker.
- Round-cap path: agent loops `ToolCall` indefinitely; orchestrator fails the turn per [`tool-use.md`](tool-use.md#streaming-with-tool-calls).

Gate: new tests green; Pi prompt #4 from [`tool-use.md`](tool-use.md#pi-listening-test-additions).

## Phase 4 — `Notifier` + `timer`

Adds `Notifier` ABC (production: background thread + heap; fake: `schedule` / `fire`), the `timer` handler, and orchestrator queue draining at end-of-conversation and inside the wake-word idle loop. `tools` config key plumbed.

Tests:
- Idle fire: `Notifier` fake fires while in wake-word mode.
- Mid-conversation fire: deferred until conversation ends, drained before re-arming.
- Multiple pending announcements drained in order.
- `timer(seconds, label)` schedules on the `Notifier` with the right arguments.

Gate: new tests green; Pi prompts #5, #6.

## Phase 5 — Ship

Update [`project-brief.md`](../project-brief.md) and [`developers.md`](../developers.md) to reflect the new ABCs and stream type; ensure `config.yaml.example` carries the v1.2 keys; mark v1.2 shipped in [`roadmap.md`](../roadmap.md).

Gate: with `tools: []`, Pi listening cycles 1–3 unchanged from v1.1.1; with defaults, all six prompts work.
