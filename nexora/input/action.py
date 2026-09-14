from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from nexora.input.input import InputManager


@dataclass(slots=True)
class ActionState:
    down: bool = False
    pressed: bool = False
    released: bool = False

    def begin_frame(self) -> None:
        self.pressed = False
        self.released = False


class ActionStateProxy:
    """
    Dynamic action state accessor.

    Preferred gameplay syntax::

        input.action_down.move_left
        input.action_pressed.jump
        input.action_released.interact

    The proxy stays callable so actions whose names are only known at
    runtime can still be queried::

        input.action_pressed("mod_action")
    """

    __slots__ = (
        "_input",
        "_state",
    )

    def __init__(
        self,
        input_manager: InputManager,
        state: str,
    ) -> None:
        self._input = input_manager
        self._state = state

    def __getattr__(
        self,
        action: str,
    ) -> bool:
        if action.startswith("_"):
            raise AttributeError(action)

        return self(action)

    def __call__(
        self,
        action: str,
    ) -> bool:
        if self._state == "down":
            return self._input.is_action_down(action)

        if self._state == "pressed":
            return self._input.is_action_pressed(action)

        if self._state == "released":
            return self._input.is_action_released(action)

        raise RuntimeError(
            f"Unknown action state: {self._state!r}"
        )
