from __future__ import annotations

from typing import Any

from nexora.nodes.node import Node
from nexora.state_machine import (
    State,
    StateMachine,
    StateTransition,
    TransitionCondition,
)


class StateMachineNode(Node):
    """Node wrapper that automatically updates a gameplay StateMachine."""

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)
        self.machine = StateMachine(owner=self)

    @property
    def current_state(self) -> State | None:
        return self.machine.current

    @property
    def current_state_name(self) -> str | None:
        return self.machine.current_name

    def add_state(self, state: State) -> State:
        return self.machine.add_state(state)

    def add_transition(
        self,
        source: str,
        target: str,
        condition: TransitionCondition,
        **kwargs,
    ) -> StateTransition:
        return self.machine.add_transition(
            source,
            target,
            condition,
            **kwargs,
        )

    def start_state_machine(
        self,
        initial: str,
        payload: Any = None,
    ) -> State:
        return self.machine.start(initial, payload)

    def change_state(
        self,
        target: str,
        payload: Any = None,
        *,
        force: bool = False,
    ) -> bool:
        return self.machine.change_state(
            target,
            payload,
            force=force,
        )

    def update(self, delta_time: float) -> None:
        if self.enabled:
            self.machine.update(delta_time)

    def fixed_update(self, delta_time: float) -> None:
        if self.enabled:
            self.machine.fixed_update(delta_time)

    def destroy(self) -> None:
        self.machine.stop()
        super().destroy()
