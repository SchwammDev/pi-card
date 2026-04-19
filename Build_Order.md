# Build Order

Sequential phases for building v1. Each phase produces something runnable or testable; later phases depend on earlier ones. Delete this file once v1 ships.

## Phase 1 — Skeleton and contracts ✅ complete

- `pyproject.toml`, package layout under `src/pi_card/`
- The four hardware ABCs in `src/pi_card/hardware/` (`AudioInput`, `AudioOutput`, `LEDController`, `AIAgent`)
- Test scaffolding: `tests/conftest.py`, `tests/dsl/` (actions + assertions), `tests/fakes/` (one fake per ABC)
- Config loader (`config.py`) with required-field validation

**Done when:** `uv run pytest` runs green on a trivial smoke test that wires fakes through an empty orchestrator.

## Phase 2 — Pipeline wrappers (against fakes) ✅ complete

- `pipeline/wake_word.py` — openWakeWord wrapper consuming `AudioInput`
- `pipeline/stt.py` — Faster-Whisper wrapper (base, int8) consuming `AudioInput`
- `pipeline/tts.py` — Piper wrapper producing frames for `AudioOutput`

**Done when:** acceptance tests for wake-word, STT, and TTS pass against fakes.

### Manual gate — TTS voice quality

Piper voice quality is subjective. Confirm now while voices are still cheap to swap. Runs on your laptop — no Pi needed.

Routes audio through our `pipeline/tts.py` into `FakeAudioOutput`, dumps the captured frames to a WAV, and plays them. This validates two things at once: the voices sound good *and* our wrapper produces frames in the contract format (16 kHz / mono / 16-bit PCM).

Save as `playground/tts_samples.py`:

```python
import wave
from pathlib import Path
from pi_card.pipeline.tts import PiperTTS
from tests.fakes.audio_output import FakeAudioOutput

OUT = Path("playground/tts_samples"); OUT.mkdir(parents=True, exist_ok=True)
SENTENCES = {
    "en_GB-alan-medium": [
        "Hello, what's the weather today?",
        "Set a timer for fifteen minutes.",
        "The meeting is on April twenty-third at three p.m.",
        "I don't know the answer to that, but I can look it up.",
        "Goodbye.",
    ],
    "fr_FR-siwis-medium": [
        "Bonjour, quel temps fait-il aujourd'hui?",
        "Règle un minuteur de quinze minutes.",
        "La réunion est le vingt-trois avril à quinze heures.",
        "Je ne connais pas la réponse, mais je peux chercher.",
        "Au revoir.",
    ],
}
for voice, lines in SENTENCES.items():
    tts = PiperTTS(voice=voice)
    for i, text in enumerate(lines):
        sink = FakeAudioOutput()
        tts.speak(text, sink)                    # adjust to the real method name
        with wave.open(str(OUT / f"{voice[:2]}_{i}.wav"), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
            w.writeframes(b"".join(sink.frames)) # adjust to whatever the fake exposes
```

Run and listen:

```bash
uv run python playground/tts_samples.py
for f in playground/tts_samples/*.wav; do echo "$f"; aplay -q "$f"; done
```

Judge: intelligible? natural enough for an assistant? French accents/liaisons acceptable? If not, pick a different voice from <https://rhasspy.github.io/piper-samples/>, update config, re-run. Don't wait until Phase 4.

## Phase 3 — Orchestrator

- `assistant.py` — top-level wiring
- `conversation.py` — turn state, in-conversation history, silence timeout, exit phrases
- Language switching (deterministic trigger-phrase match, ack in new language)
- Error handling and LED feedback per the spec

**Done when:** all acceptance tests in `tests/features/` pass against fakes.

## Phase 4 — Production hardware adapters (parallel-friendly)

These four are independent and tested against the same fakes/contracts from Phase 1. Build in parallel if convenient:

- `adapters/respeaker_input.py`
- `adapters/respeaker_leds.py`
- `adapters/usb_speaker.py`
- `adapters/openai_agent.py`

### Manual gate — per-adapter hardware bring-up

Each adapter needs a human in front of the Pi the first time. Where a Phase 2 wrapper already consumes the adapter, route through it — that exercises the seam between the adapter and the rest of the package, not just the hardware.

First, find your ALSA device IDs once and reuse them:

```bash
arecord -l   # note the ReSpeaker card name, e.g. "seeed4micvoicec"
aplay   -l   # note the USB speaker card name, e.g. "Device"
```

**ReSpeaker input — via `pipeline/stt.py`.** Captures 5 s from the real mic and prints what Faster-Whisper heard. Tests the mic *and* that the captured frames are valid input to STT.

Save as `playground/mic_check.py`:

```python
from pi_card.adapters.respeaker_input import ReSpeakerInput
from pi_card.pipeline.stt import WhisperSTT

mic = ReSpeakerInput()
stt = WhisperSTT(language="en")
print("Speak for 5 seconds...")
audio = mic.record(seconds=5)               # adjust to the real method name
print("Heard:", stt.transcribe(audio))
```

Pass: transcript roughly matches what you said. Garbled output ⇒ wrong sample rate, wrong channel count, or a mic-gain problem.

**USB speaker — via `pipeline/tts.py`.** End-to-end synth-and-play through our wrapper into the real adapter.

Save as `playground/speaker_check.py`:

```python
from pi_card.adapters.usb_speaker import USBSpeakerOutput
from pi_card.pipeline.tts import PiperTTS

PiperTTS(voice="en_GB-alan-medium").speak(
    "If you can hear this clearly, the speaker adapter works.",
    USBSpeakerOutput(),
)
```

Pass: audible at usable volume, no crackle, no buffer-underrun warnings in the log. Silence ⇒ probably HDMI selected; re-check `aplay -l`.

**ReSpeaker LEDs — adapter only** (no Phase 2 wrapper consumes LEDs). Save as `playground/leds_check.py`:

```python
import time
from pi_card.adapters.respeaker_leds import ReSpeakerLEDs

leds = ReSpeakerLEDs()
for state in ["listening", "thinking", "error"]:
    print(state); leds.set(state); time.sleep(2)
leds.off()
```

Pass: pulsing blue → pulsing green → red flash, each visually distinct and matching the spec.

**OpenAI agent — adapter only** (no wrapper layer; the orchestrator calls it directly). Save as `playground/agent_check.py`:

```python
import time
from pi_card.config import load_config
from pi_card.adapters.openai_agent import OpenAIAgent

agent = OpenAIAgent(load_config())
t0 = time.perf_counter()
reply = agent.reply([{"role": "user", "content": "Say hello in one sentence."}])
print(f"{time.perf_counter() - t0:.2f}s  →  {reply}")
```

Pass: sensible reply in under ~2 s. If it's already 5+ s here, the full pipeline will feel sluggish — investigate before moving on.

Run each with `uv run python playground/<name>.py`. Method names above are placeholders — adjust to whatever you actually built.

### Manual gate — full conversation, ears only

With all four adapters wired in, run the assistant and have a real conversation. You're judging *felt* quality, which acceptance tests cannot.

```bash
uv run python -m pi_card --log-level INFO --debug-transcripts
# Watch the log in another terminal:
tail -f ~/.local/state/pi-card/logs/transcripts.log
```

Then:

- Say "Computer", ask a question, listen to the reply.
- Ask a follow-up that depends on the previous turn (tests in-conversation history end-to-end).
- Stay silent and confirm the 8-second timeout returns to wake-word mode.
- Say "goodbye" mid-conversation and confirm explicit exit works.
- Switch language mid-session via the trigger phrase; confirm the ack comes back in the new language and subsequent replies stay in it.
- Unplug the network briefly and ask something; confirm the spoken error cue plays and the LED flashes red.

Judge: does the multi-turn rhythm feel natural? Is end-to-end latency tolerable (wake → reply start)? Does the 8s silence timeout feel right, or should the default change?

**Done when:** the assistant runs end-to-end on a Pi with real hardware and the manual conversation gate above passes.

## Phase 5 — Packaging

- `cli.py` and `__main__.py` with the documented flags
- `Makefile` targets: `install`, `run`, `service`, `uninstall`, `clean`
- systemd unit for auto-start
- `config.yaml.example` with all defaults documented

**Done when:** `make install && make service` brings the assistant up on a fresh Pi.

### Manual gate — fresh-Pi install

The only way to catch missing system deps, wrong paths, or systemd unit mistakes is to install on a Pi you haven't been developing on.

- Flash a clean Raspberry Pi OS image, configure the ReSpeaker HAT per its vendor instructions, then clone this repo.
- Run `make install`. Pass: no errors, default config written, venv created.
- Edit `config.yaml` to add `base_url`, `api_key`, `model`. Run `make run`. Pass: assistant comes up, wake word works, one round-trip succeeds.
- Run `make service`, then **reboot the Pi**. Pass: after boot, with no manual intervention, saying "Computer" gets a response.
- Check `journalctl -u pi-card` for warnings — anything noisy on a clean install is a packaging bug worth fixing now.
- Run `make uninstall`. Pass: service stopped and removed, no leftover files outside the repo.

## Out of Scope for v1

- Streaming TTS (deferred to v2; see `Project_Overview.md`)
- Cross-conversation memory (interface seam exists; no implementation)
- Auto language detection
