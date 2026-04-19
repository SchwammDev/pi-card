# Manual Gates — Runbook

Human-only scripts and commands for the manual gates in `Build_Order.md`. Delete this file once v1 ships.

## Phase 2 — TTS voice quality

Routes audio through `pipeline/tts.py` into `FakeAudioOutput`, dumps frames to WAV, plays them. Runs on your laptop — no Pi needed.

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

Alternative voices: <https://rhasspy.github.io/piper-samples/>

## Phase 4 — Per-adapter hardware bring-up

Find your ALSA device IDs once and reuse them:

```bash
arecord -l   # note the ReSpeaker card name, e.g. "seeed4micvoicec"
aplay   -l   # note the USB speaker card name, e.g. "Device"
```

### ReSpeaker input — via `pipeline/stt.py`

Captures 5 s from the real mic and prints what Faster-Whisper heard. Tests the mic *and* that captured frames are valid input to STT.

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

Garbled output ⇒ wrong sample rate, wrong channel count, or mic-gain problem.

### USB speaker — via `pipeline/tts.py`

End-to-end synth-and-play through our wrapper into the real adapter.

Save as `playground/speaker_check.py`:

```python
from pi_card.adapters.usb_speaker import USBSpeakerOutput
from pi_card.pipeline.tts import PiperTTS

PiperTTS(voice="en_GB-alan-medium").speak(
    "If you can hear this clearly, the speaker adapter works.",
    USBSpeakerOutput(),
)
```

Silence ⇒ probably HDMI selected; re-check `aplay -l`.

### ReSpeaker LEDs

Save as `playground/leds_check.py`:

```python
import time
from pi_card.adapters.respeaker_leds import ReSpeakerLEDs

leds = ReSpeakerLEDs()
for state in ["listening", "thinking", "error"]:
    print(state); leds.set(state); time.sleep(2)
leds.off()
```

### OpenAI agent

Save as `playground/agent_check.py`:

```python
import time
from pi_card.config import load_config
from pi_card.adapters.openai_agent import OpenAIAgent

agent = OpenAIAgent(load_config())
t0 = time.perf_counter()
reply = agent.reply([{"role": "user", "content": "Say hello in one sentence."}])
print(f"{time.perf_counter() - t0:.2f}s  →  {reply}")
```

Run each with `uv run python playground/<name>.py`. Method names above are placeholders — adjust to whatever you actually built.

## Phase 4 — Full conversation, ears only

```bash
uv run python -m pi_card --log-level INFO --debug-transcripts
# In another terminal:
tail -f ~/.local/state/pi-card/logs/transcripts.log
```

Run through the conversation script listed in `Build_Order.md` (wake word, follow-up, silence timeout, goodbye, language switch, network-unplugged error).

## Phase 5 — Fresh-Pi install

- Flash a clean Raspberry Pi OS image, configure the ReSpeaker HAT per its vendor instructions, then clone this repo.
- `make install`
- Edit `config.yaml` to add `base_url`, `api_key`, `model`. Run `make run`.
- `make service`, then **reboot the Pi**.
- `journalctl -u pi-card` — check for warnings.
- `make uninstall`.
