from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .machine import StateMachine


class State:
    """Base class for a gameplay state.

    Subclass this and override the lifecycle hooks you need. A State is
    registered in exactly one :class:`StateMachine` at a time.
    """

    def __init__(self, name: str) -> None:
        name = str(name).strip()
        if not name:
            raise ValueError("State name cannot be empty.")

        self.name = name
        self._machine: StateMachine | None = None

    @property
    def machine(self) -> StateMachine:
        machine = self._machine
        if machine is None:
            raise RuntimeError(
                f"State {self.name!r} is not registered in a StateMachine."
            )
        return machine

    @property
    def blackboard(self) -> dict[str, Any]:
        return self.machine.blackboard

    def _bind(self, machine: StateMachine) -> None:
        if self._machine is not None and self._machine is not machine:
            raise RuntimeError(
                f"State {self.name!r} is already registered in another StateMachine."
            )
        self._machine = machine

    def _unbind(self, machine: StateMachine) -> None:
        if self._machine is machine:
            self._machine = None

    def enter(
        self,
        previous: State | None,
        payload: Any = None,
    ) -> None:
        """Called after this state becomes current."""

    def exit(self, next_state: State | None) -> None:
        """Called before this state stops being current."""

    def update(self, delta_time: float) -> None:
        """Per-frame state update."""

    def fixed_update(self, delta_time: float) -> None:
        """Fixed-timestep state update."""
