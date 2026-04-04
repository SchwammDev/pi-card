# Raspberry Pi AI Voice Assistant

Lightweight voice assistant that runs on a Raspberry Pi 4+. Listens for a wake word, transcribes user speech, dispatches to an AI agent, and speaks the response.

## Supported Languages

- English
- French

## Tech Stack

- **Language:** Python
- **Wake word detection:** openWakeWord (offline, swappable to Porcupine if accuracy needs arise)
- **Speech-to-text:** Faster-Whisper (offline, multilingual — user specifies language)
- **Text-to-speech:** Piper (offline, fast on Pi 4; swappable to cloud TTS later)
- **AI agent:** OpenAI-compatible API (user-configurable provider)

## Hardware & Audio

- **Audio input** — ReSpeaker 4-Mic HAT (I2S)
- **Audio output** — USB speakers
- **Privacy** — _TBD: Everything offline except the AI agent call. Worth stating explicitly as a design constraint._

## Runtime Behavior

- **Conversation mode** — Multi-turn. After each response, the mic stays open for follow-ups. Conversation ends on silence timeout (default: 8s, configurable) or explicit exit ("goodbye", "that's all"), returning to wake-word mode.
- **Concurrency model** — Sequential pipeline (listen → transcribe → query → speak) to start. Later, stream AI response into TTS in sentence-sized chunks for lower perceived latency.
- **Error handling & feedback:**
  - **Network / API failure** — Play spoken error cue ("I can't reach my brain right now"), flash LED red, return to wake-word mode. No silent retries.
  - **Low-confidence STT** — Ask "Sorry, could you repeat that?" and re-listen. Max retries configurable (default: 2), then audio error cue + red LED, return to wake-word mode.
  - **TTS failure** — Play generic error tone, log error, return to wake-word mode.
  - **Audio hardware issues** — Detect on startup, fail fast with clear log message. LED solid red if available.
  - **LED feedback** — ReSpeaker HAT LEDs: pulsing blue = listening, pulsing green = thinking/processing, red flash = error.
  - **Logging** — Local error log with rotation for debugging.

## User-Facing Setup

- **Configuration** — _TBD: How does the user set language, API provider, API keys, wake word? Config file, CLI flags, web UI?_
- **Installation & deployment** — _TBD: How does this get onto the Pi? pip install, Docker, setup script?_

