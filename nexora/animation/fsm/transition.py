from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .machine import StateMachine


TransitionCondition = Callable[["StateMachine"], bool]


@dataclass(slots=True)
class StateTransition:
    source: str
    target: str
    condition: TransitionCondition
    priority: int = 0
    min_time: float = 0.0
    name: str | None = None
    enabled: bool = True
    order: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        self.source = str(self.source).strip()
        self.target = str(self.target).strip()
        self.priority = int(self.priority)
        self.min_time = float(self.min_time)

        if not self.source:
            raise ValueError("Transition source cannot be empty.")
        if not self.target:
            raise ValueError("Transition target cannot be empty.")
        if self.min_time < 0.0:
            raise ValueError("Transition min_time cannot be negative.")
        if not callable(self.condition):
            raise TypeError("Transition condition must be callable.")

        if self.name is None:
            self.name = f"{self.source}->{self.target}"
        else:
            self.name = str(self.name)
