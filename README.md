# pi-card

Lightweight voice assistant for Raspberry Pi 4+. Wake word → speech-to-text → AI reply → text-to-speech — everything on the device except the LLM call.

## Features

- **Multi-turn conversations.** Mic stays open between turns until silence timeout or an explicit "goodbye".
- **English and French.** Switchable mid-session by voice command.
- **Offline pipeline.** openWakeWord, Faster-Whisper (`base`/`int8`), Piper.
- **Pluggable AI agent.** Any OpenAI-compatible chat-completions endpoint.
- **LED + audio cues.** Listening / thinking / error feedback via the ReSpeaker LEDs.
- **Headless boot.** Systemd auto-start on reboot.

## Hardware

- Raspberry Pi 4 or 5
- ReSpeaker 4-Mic HAT (I2S input + LEDs)
- Speaker on the 3.5 mm jack, USB, or HDMI

## Quick start

If your Pi already has `git`, `uv`, `libportaudio2`, the ReSpeaker driver, and a working ALSA default:

```bash
git clone <repo URL>
cd pi-card
make install
nano ~/.config/pi-card/config.yaml   # set base_url, api_key, model
make run
```

For a fresh Pi (Pi OS prereqs, ReSpeaker driver install, ALSA setup, headless service), follow [`docs/install.md`](docs/install.md).

## Configuration

`~/.config/pi-card/config.yaml`. Required: `base_url`, `api_key`, `model`. See [`config.yaml.example`](config.yaml.example).

## Voice commands

| Intent | Say (EN) | Say (FR) |
|---|---|---|
| Switch language | "switch to French" | "parle anglais" |
| End conversation | "goodbye", "that's all" | "au revoir", "c'est tout" |

## Documentation

- [`docs/project-brief.md`](docs/project-brief.md) — design and architecture
- [`docs/developers.md`](docs/developers.md) — workflow, test conventions, listening protocol, extension points
- [`docs/roadmap.md`](docs/roadmap.md) — upcoming releases and feature plans

## Development

Python 3.11+, uv. Run tests with `./run-tests.sh`. See [`docs/developers.md`](docs/developers.md).

License: see [`LICENSE`](LICENSE).
