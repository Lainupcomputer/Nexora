from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ActionState:
    down: bool = False
    pressed: bool = False
    released: bool = False

    def begin_frame(self) -> None:
        self.pressed = False
        self.released = False