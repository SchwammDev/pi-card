from abc import ABC, abstractmethod
from enum import Enum


class LEDState(Enum):
    OFF = "off"
    LISTENING = "listening"
    THINKING = "thinking"
    ERROR = "error"


class LEDController(ABC):
    @abstractmethod
    def set_state(self, state: LEDState) -> None:
        """Show the given feedback state on the LEDs."""
