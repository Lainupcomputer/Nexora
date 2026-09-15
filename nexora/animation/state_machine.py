from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable

from nexora.animation.player import AnimationPlayer


Condition = Callable[[], bool]


@dataclass(slots=True)
class AnimationTransition:
    source: str
    target: str
    condition: Condition
    priority: int = 0
    restart: bool = False
    order: int = field(default=0, repr=False)


class AnimationStateMachine:
    """Small runtime state machine layered over AnimationPlayer."""

    ANY = "*"

    def __init__(self, player: AnimationPlayer) -> None:
        self.player = player
        self._states: dict[str, str] = {}
        self._transitions: list[AnimationTransition] = []
        self._order = 0
        self.current_state: str | None = None
        self.state_changed = player.create_signal(f"{player.name}.state_changed")

    def add_state(self, name: str, animation: str) -> None:
        name = str(name).strip()
        if not name:
            raise ValueError("State name cannot be empty.")
        self._states[name] = str(animation)

    def remove_state(self, name: str) -> None:
        self._states.pop(name, None)
        self._transitions = [
            transition
            for transition in self._transitions
            if transition.source != name and transition.target != name
        ]
        if self.current_state == name:
            self.current_state = None

    def add_transition(
        self,
        source: str,
        target: str,
        condition: Condition,
        *,
        priority: int = 0,
        restart: bool = False,
    ) -> AnimationTransition:
        if source != self.ANY and source not in self._states:
            raise KeyError(f"Unknown animation state: {source}")
        if target not in self._states:
            raise KeyError(f"Unknown animation state: {target}")
        if not callable(condition):
            raise TypeError("Animation transition condition must be callable.")
        transition = AnimationTransition(
            source=source,
            target=target,
            condition=condition,
            priority=int(priority),
            restart=bool(restart),
            order=self._order,
        )
        self._order += 1
        self._transitions.append(transition)
        self._transitions.sort(key=lambda item: (-item.priority, item.order))
        return transition

    def set_state(self, name: str, *, restart: bool = False) -> None:
        if name not in self._states:
            raise KeyError(f"Unknown animation state: {name}")
        previous = self.current_state
        if previous == name and not restart:
            return
        self.current_state = name
        self.player.play(self._states[name], restart=restart)
        self.state_changed.emit(previous, name)

    def update(self) -> bool:
        if self.current_state is None:
            return False
        for transition in self._transitions:
            if transition.source not in (self.ANY, self.current_state):
                continue
            if transition.target == self.current_state and not transition.restart:
                continue
            if transition.condition():
                self.set_state(transition.target, restart=transition.restart)
                return True
        return False

    def animation_for(self, state: str) -> str:
        return self._states[state]

    @property
    def states(self) -> tuple[str, ...]:
        return tuple(self._states)
