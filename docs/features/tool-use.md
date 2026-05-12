# v1.2 — Tool use

The voice assistant gains the ability to invoke tools via the OpenAI chat-completions `tools` field. v1.2 ships three tools — `current_time`, `current_date`, `timer` — chosen to harden the dispatch loop while introducing the out-of-conversation-loop channel that future tools (services, sub-agents, ambient notifications) will also need.

## Tools

| Name | Args | Returns | Notes |
|------|------|---------|-------|
| `current_time` | — | ISO + human-readable string | Pi-local clock |
| `current_date` | — | ISO + human-readable string | Pi-local clock |
| `timer` | `seconds: int`, `label?: string` | confirmation string | Schedules an announcement via `Notifier` |

No `cancel_timer` or `list_timers` in v1.2 — add when a user asks for them.

## Dispatch architecture

Three components, injected into the assistant:

- **`AIAgent`** — narrowed responsibility: talks to the LLM. Signature becomes `stream(messages, tools=None) -> Iterator[StreamEvent]` where `StreamEvent` is `TextDelta | ToolCall | TurnDone`. Surfaces what the model emitted; does not execute anything.
- **`ToolDispatcher`** — wraps `AIAgent` + `ToolRegistry`. Owns the tool-call loop: execute, append `role: "tool"` messages, re-stream, cap at `max_tool_rounds`. Exposes `stream(messages) -> Iterator[str]` to the orchestrator — same shape as today, so `assistant.py` is unchanged at the call site.
- **`ToolRegistry`** — lookup of tool name → handler. Each handler is constructed with whatever it needs (a `Clock` for time tools, a `Notifier` for `timer`, an `AIAgent` for a future sub-agent tool, an HTTP client for service tools). Tools do not know about each other.

*Why a separate dispatcher rather than inlining the loop into the orchestrator:* test isolation. Conversation-lifecycle tests stay free of tool-loop setup; tool-loop tests stay free of wake-word/STT setup.

*Why not put tool execution on `AIAgent`:* a tool may itself invoke an `AIAgent` (sub-agent pattern), and many future tools call external services. Tool dispatch is an assistant capability, not a property of any one LLM client. Putting it on `AIAgent` would force every future adapter (e.g. local llama.cpp) to re-implement it.

## Streaming with tool calls

A turn produces a sequence of text deltas and tool_call deltas, terminated by a finish reason of either `stop` or `tool_calls`.

- **Prelude text before tool_calls.** The system prompt instructs the model not to narrate tool use, so prelude should be rare. When it does occur, the dispatcher forwards it as `TextDelta` events; the chunker speaks it as today. *Why not buffer until the tool round resolves:* holding speech to wait for a tool round we did not know was coming reintroduces the first-word latency the chunker exists to avoid.
- **After tool execution.** Dispatcher appends the tool result(s) as `role: "tool"` messages and re-streams. Final text deltas continue on the same TTS lane.
- **Round cap.** `max_tool_rounds` (default 3) bounds latency and prevents loops. Hitting the cap is a turn failure: spoken error cue + red LED + return to wake-word mode.

## System prompt addendum

Appended to the existing prompt: "When you use a tool, just call it — do not narrate or announce the call. Speak only the answer after the result is in."

## Notifier — out-of-band speech

New ABC. Owns scheduled announcements; runs a background thread. The `timer` tool handler schedules events on it. When an event fires, the `Notifier` hands the assistant an announcement (short tone + spoken text) to play.

Behavior depends on assistant state at fire time:

| State | Behavior |
|-------|----------|
| Idle (wake-word mode) | Play tone + announcement immediately, then return to wake-word mode. |
| Conversation active (listening, processing, or speaking) | Defer until the conversation ends; drain pending announcements before re-arming wake-word. |

*Why defer mid-conversation:* v1.2 does not yet have TTS lane cancellation. v1.3 (barge-in) introduces it and will upgrade timer interrupts to cut in mid-reply.

Multiple concurrent timers are supported. Pending timers are in memory only — process restart wipes them. Documented limitation; revisit if a user asks.

## Tool errors

A tool handler may raise or return an error. The error string is fed back to the model as the `role: "tool"` message content; the model recovers in its next round (typically by apologizing or retrying with corrected arguments). No distinct spoken cue for tool errors — they are internal to the turn.

*Why not hard-fail on tool errors:* v1.2 tools have negligible failure surface (`current_time` cannot meaningfully fail; `timer` only fails on bad args, which is exactly the recover-via-LLM case). When a future tool has real failure modes (network, filesystem, external API), split tool *invocation* errors (recover via LLM) from tool *handler* errors (hard fail, spoken cue, red LED).

## Configuration

New keys under the AI agent config block:

- `max_tool_rounds: int` — cap on tool-call rounds per turn. Default `3`.
- `tools: list[str]` — enabled tools. Default `["current_time", "current_date", "timer"]`. Empty list disables tool use entirely; `AIAgent.stream` is then invoked without the `tools` field, preserving today's behavior bit-for-bit.

## Testing

- `AIAgent` fake yields canned `StreamEvent` sequences (text deltas, tool_calls, turn done) so the dispatcher loop can be exercised without a real LLM.
- `Clock` fake for time tools.
- `Notifier` fake records scheduled events and exposes a `fire(name)` method for tests to trigger announcements deterministically; no real wall-clock waits.
- Acceptance tests live in `tests/features/tool_use.py`.

## Pi listening test additions

Append to the listening protocol in `developers.md`:

| # | Prompt | Listen for |
|---|---|---|
| 4 | "What time is it?" | Tool round resolves; spoken reply is just the time, no narration. |
| 5 | "Set a timer for 15 seconds." | Confirmation spoken immediately. After conversation ends, tone + announcement fires near the 15 s mark. |
| 6 | "Set a 10 second timer and a 20 second timer." | Both announcements fire, in order, after conversation ends. |

## Out of scope for v1.2

- Persisted timers across restart.
- `cancel_timer` / `list_timers` tools.
- Timer announcements interrupting playback (lane cancellation — v1.3).
- Parallel tool execution within a single round (sequential only).
- Per-tool LED cues or per-tool latency surfaces.
