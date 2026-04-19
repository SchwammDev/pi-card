# Hardware Interfaces

Production code depends on abstract interfaces (Python ABCs), never on concrete hardware. Each hardware boundary has a corresponding ABC with a production implementation and a test fake.

## Interfaces

| ABC | Production | Test Fake | Responsibility |
|-----|------------|-----------|----------------|
| `AudioInput` | ReSpeaker 4-Mic HAT | Returns pre-recorded audio bytes | Mic capture |
| `AudioOutput` | USB speakers | Records what was "played" | Speaker playback |
| `LEDController` | ReSpeaker HAT LEDs | Records state changes | LED feedback |
| `AIAgent` | OpenAI-compatible API client | Returns canned responses | AI provider communication |

## Audio Format

`AudioInput` and `AudioOutput` exchange frames in a single fixed format so wake-word, STT, and TTS components can pass data through without resampling:

- **Sample rate:** 16 kHz
- **Channels:** 1 (mono)
- **Sample format:** 16-bit signed PCM, little-endian
- **Frame size (input):** 1280 samples (80 ms) — matches openWakeWord's native chunk

## Injection

Dependencies are passed via constructor injection. No service locators, no DI frameworks.

```python
# Production
assistant = VoiceAssistant(
    audio_in=ReSpeakerInput(),
    audio_out=USBSpeakerOutput(),
    leds=ReSpeakerLEDs(),
    agent=OpenAIAgent(config),
)

# Test
assistant = VoiceAssistant(
    audio_in=FakeAudioInput(utterances=["What's the weather?"]),
    audio_out=FakeAudioOutput(),
    leds=FakeLEDController(),
    agent=FakeAIAgent(responses=["It's sunny today."]),
)
```
