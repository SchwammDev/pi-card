from pi_card.hardware.leds import LEDController, LEDState


class FakeLEDController(LEDController):
    """Records every state change so tests can assert on LED feedback."""

    def __init__(self):
        self.states: list[LEDState] = []

    def set_state(self, state: LEDState) -> None:
        self.states.append(state)

    @property
    def current(self) -> LEDState | None:
        return self.states[-1] if self.states else None
