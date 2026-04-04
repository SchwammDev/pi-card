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

