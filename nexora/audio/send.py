from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(slots=True)
class AudioSend:
    """A parallel routing edge between two mixer buses."""

    source_bus_id: str
    target_bus_id: str
    amount: float = 1.0
    pre_fader: bool = False
    enabled: bool = True
    id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self) -> None:
        self.amount = self.amount

    def __setattr__(self, name: str, value) -> None:
        if name == "amount":
            value = float(value)
            if value < 0.0:
                raise ValueError("Audio send amount must not be negative.")
        object.__setattr__(self, name, value)
