import math
import threading
import time

from pi_card.hardware.leds import LEDController, LEDState

NUM_LEDS = 12
PULSE_PERIOD_S = 2.0
PULSE_STEP_S = 0.05
BRIGHTNESS_MAX = 20  # APA102 global brightness is 5-bit (0-31)

_COLOURS: dict[LEDState, tuple[int, int, int] | None] = {
    LEDState.OFF: None,
    LEDState.LISTENING: (0, 0, 255),
    LEDState.THINKING: (0, 255, 0),
    LEDState.ERROR: (255, 0, 0),
}


class ReSpeakerLEDs(LEDController):
    """LEDController for the ReSpeaker 4-Mic HAT's 12 APA102 LEDs.

    Pulses the whole ring in a background thread; red is shown solid since
    the spec describes it as a "flash" that must remain visible briefly even
    if a new state follows almost immediately."""

    def __init__(self, *, driver=None):
        self._driver = driver if driver is not None else _APA102SpiDriver(NUM_LEDS)
        self._lock = threading.Lock()
        self._state = LEDState.OFF
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def set_state(self, state: LEDState) -> None:
        with self._lock:
            self._state = state

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)
        self._paint((0, 0, 0), brightness=0)
        self._driver.close()

    def _run(self) -> None:
        t = 0.0
        while not self._stop.is_set():
            with self._lock:
                state = self._state
            colour = _COLOURS[state]
            if colour is None:
                self._paint((0, 0, 0), brightness=0)
            elif state == LEDState.ERROR:
                self._paint(colour, brightness=BRIGHTNESS_MAX)
            else:
                phase = (math.sin(2 * math.pi * t / PULSE_PERIOD_S) + 1) / 2
                self._paint(colour, brightness=max(1, int(phase * BRIGHTNESS_MAX)))
            time.sleep(PULSE_STEP_S)
            t += PULSE_STEP_S

    def _paint(self, colour: tuple[int, int, int], *, brightness: int) -> None:
        r, g, b = colour
        for i in range(NUM_LEDS):
            self._driver.set_pixel(i, r, g, b, brightness)
        self._driver.show()


class _APA102SpiDriver:
    """Minimal APA102 driver over Linux SPI. Enough to drive a small ring
    and nothing more. Wire protocol: 4 bytes of zeros (start frame), then
    4 bytes per LED [0xE0|brightness, B, G, R], then enough 1-bits to
    clock the last LED's data through the daisy chain."""

    def __init__(self, num_leds: int, *, bus: int = 0, device: int = 0, max_speed_hz: int = 8_000_000):
        import spidev  # type: ignore[import-not-found]

        self._spi = spidev.SpiDev()
        self._spi.open(bus, device)
        self._spi.max_speed_hz = max_speed_hz
        self._num_leds = num_leds
        self._pixels = [(0, 0, 0, 0)] * num_leds

    def set_pixel(self, index: int, r: int, g: int, b: int, brightness: int) -> None:
        br = max(0, min(31, brightness))
        self._pixels[index] = (r & 0xFF, g & 0xFF, b & 0xFF, br)

    def show(self) -> None:
        buf = [0, 0, 0, 0]
        for r, g, b, br in self._pixels:
            buf.extend([0xE0 | br, b, g, r])
        buf.extend([0xFF] * ((self._num_leds + 15) // 16))
        self._spi.xfer2(buf)

    def close(self) -> None:
        self._spi.close()
