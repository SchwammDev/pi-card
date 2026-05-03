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

## Phase 5 — Full conversation, ears only

```bash
uv run python -m pi_card --log-level INFO --debug-transcripts
# In another terminal:
tail -f ~/.local/state/pi-card/logs/transcripts.log
```

Run through the conversation script listed in `Build_Order.md` (wake word, follow-up, silence timeout, goodbye, language switch, network-unplugged error).

## Phase 5 — Fresh-Pi install

Assumes a freshly flashed Raspberry Pi OS image with network access.

### Prerequisites

```bash
sudo apt update
sudo apt install -y git libportaudio2

curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env
which uv
```

### ReSpeaker HAT driver

The HinTak fork uses one **branch per kernel** (not tags). Pick the branch matching `uname -r`:

```bash
git clone https://github.com/HinTak/seeed-voicecard
cd seeed-voicecard
git checkout v$(uname -r | cut -d. -f1-2)   # e.g. v6.12 for kernel 6.12.x
sudo ./install.sh
sudo reboot
```

After reboot, `arecord -l` should list `seeed-4mic-voicecard` (or your variant).

### ALSA default device

Pi OS Trixie ships without a usable default sink — sounddevice/portaudio (used by pi-card's adapters) needs one. Test:

```bash
speaker-test -t sine -f 440 -l 1 -c 1
```

If it errors with "No such device", find your output card index in `aplay -l` (typically `0` for the headphone jack) and write `~/.asoundrc`:

```
pcm.!default {
    type plug
    slave.pcm "hw:0,0"
}

ctl.!default {
    type hw
    card 0
}
```

Re-run `speaker-test` to confirm a tone comes out.

### Hardware roundtrip

Mic and speaker via raw ALSA before involving pi-card. Replace `<seeed-card>` with the index from `arecord -l`:

```bash
arecord -D plughw:<seeed-card>,0 -f S16_LE -r 16000 -c 2 -d 5 /tmp/mic_test.wav
aplay /tmp/mic_test.wav
```

Speak during the 5 s window. You should hear yourself.

### pi-card install and first run

```bash
cd ~
git clone <pi-card repo URL>
cd pi-card
make install
nano ~/.config/pi-card/config.yaml   # set base_url, api_key, model
make run
```

First run downloads Piper voices, the Whisper model, and the openWakeWord models — expect ~1–2 min on a working network. Subsequent runs are fast. Try the wake word; expect a reply.

### Service install and headless boot

```bash
make service
sudo loginctl enable-linger $USER   # without this the user unit only starts after login
sudo reboot
```

After reboot, log back in. The service should be running unattended (LED + audio cue, wake word works). Check the journal:

```bash
systemctl --user status pi-card.service
journalctl _SYSTEMD_USER_UNIT=pi-card.service -b --no-pager
```

Note: `journalctl --user -u …` returns nothing on default Pi OS — journald doesn't keep a per-user journal. The `_SYSTEMD_USER_UNIT=` field-filter reads user-unit entries from the system journal, which does work. Persistent journals across reboots are off by default; check within the same boot.

Anything noisy in the journal is a packaging bug worth fixing now.

### Uninstall

```bash
systemctl --user stop pi-card.service   # no sudo — sudo strips the user bus env
make uninstall

ls ~/.config/pi-card ~/.local/state/pi-card ~/.local/share/pi-card 2>&1   # all "No such file"
systemctl --user status pi-card.service 2>&1 | head -3                    # "not-found"
```
