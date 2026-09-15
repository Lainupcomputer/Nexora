from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from nexora.signals import Signal

from .state import State
from .transition import StateTransition, TransitionCondition


class StateMachine:
    """Reusable finite state machine for gameplay logic.

    It is intentionally independent of the Scene/Node system so it can be
    embedded in Nodes, controllers, AI objects, tests, and editor tools.
    """

    ANY_STATE = "*"

    def __init__(
        self,
        *,
        owner: object | None = None,
        blackboard: dict[str, Any] | None = None,
    ) -> None:
        self.owner = owner
        self.blackboard: dict[str, Any] = (
            blackboard if blackboard is not None else {}
        )

        self._states: dict[str, State] = {}
        self._transitions: list[StateTransition] = []
        self._transition_order = 0

        self._current: State | None = None
        self._previous: State | None = None
        self._state_time = 0.0
        self._paused = False
        self._running = False

        self._updating = False
        self._pending_change: tuple[str, Any, bool] | None = None

        self.state_entered = Signal(
            "state_machine.state_entered",
            owner=owner,
        )
        self.state_exited = Signal(
            "state_machine.state_exited",
            owner=owner,
        )
        self.state_changed = Signal(
            "state_machine.state_changed",
            owner=owner,
        )
        self.transition_triggered = Signal(
            "state_machine.transition_triggered",
            owner=owner,
        )
        self.started = Signal(
            "state_machine.started",
            owner=owner,
        )
        self.stopped = Signal(
            "state_machine.stopped",
            owner=owner,
        )

    @property
    def current(self) -> State | None:
        return self._current

    @property
    def current_name(self) -> str | None:
        return self._current.name if self._current is not None else None

    @property
    def previous(self) -> State | None:
        return self._previous

    @property
    def state_time(self) -> float:
        return self._state_time

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def running(self) -> bool:
        return self._running

    @property
    def states(self) -> tuple[State, ...]:
        return tuple(self._states.values())

    @property
    def transitions(self) -> tuple[StateTransition, ...]:
        return tuple(self._transitions)

    def has_state(self, name: str) -> bool:
        return str(name) in self._states

    def get_state(self, name: str) -> State:
        key = str(name)
        try:
            return self._states[key]
        except KeyError as exc:
            raise KeyError(f"Unknown state: {key!r}.") from exc

    def add_state(self, state: State) -> State:
        if not isinstance(state, State):
            raise TypeError("state must be a State instance.")
        if state.name in self._states:
            raise ValueError(f"State {state.name!r} is already registered.")

        state._bind(self)
        self._states[state.name] = state
        return state

    def add_states(self, states: Iterable[State]) -> None:
        for state in states:
            self.add_state(state)

    def remove_state(self, name: str) -> State:
        key = str(name)
        state = self.get_state(key)

        if self._current is state:
            raise RuntimeError("Cannot remove the currently active state.")

        del self._states[key]
        state._unbind(self)
        self._transitions = [
            transition
            for transition in self._transitions
            if transition.source != key and transition.target != key
        ]
        return state

    def add_transition(
        self,
        source: str,
        target: str,
        condition: TransitionCondition,
        *,
        priority: int = 0,
        min_time: float = 0.0,
        name: str | None = None,
        enabled: bool = True,
    ) -> StateTransition:
        source = str(source)
        target = str(target)

        if source != self.ANY_STATE and source not in self._states:
            raise KeyError(f"Unknown transition source state: {source!r}.")
        if target not in self._states:
            raise KeyError(f"Unknown transition target state: {target!r}.")

        transition = StateTransition(
            source=source,
            target=target,
            condition=condition,
            priority=priority,
            min_time=min_time,
            name=name,
            enabled=enabled,
            order=self._transition_order,
        )
        self._transition_order += 1
        self._transitions.append(transition)
        return transition

    def remove_transition(self, transition: StateTransition) -> bool:
        try:
            self._transitions.remove(transition)
        except ValueError:
            return False
        return True

    def start(self, initial: str, payload: Any = None) -> State:
        if self._running:
            raise RuntimeError("StateMachine is already running.")

        state = self.get_state(initial)
        self._running = True
        self._paused = False
        self._previous = None
        self._current = state
        self._state_time = 0.0
        self._pending_change = None

        state.enter(None, payload)
        self.started.emit(self, state)
        self.state_entered.emit(self, state, None, payload)
        self.state_changed.emit(self, None, state)
        return state

    def stop(self) -> None:
        if not self._running:
            return

        current = self._current
        if current is not None:
            current.exit(None)
            self.state_exited.emit(self, current, None)

        self._previous = current
        self._current = None
        self._state_time = 0.0
        self._running = False
        self._paused = False
        self._pending_change = None
        self.stopped.emit(self, current)

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def change_state(
        self,
        target: str,
        payload: Any = None,
        *,
        force: bool = False,
    ) -> bool:
        target = str(target)
        self.get_state(target)

        if not self._running:
            raise RuntimeError("StateMachine must be started before changing state.")

        if self._updating:
            self._pending_change = (target, payload, bool(force))
            return True

        return self._apply_change(target, payload, bool(force))

    def _apply_change(
        self,
        target: str,
        payload: Any,
        force: bool,
    ) -> bool:
        next_state = self.get_state(target)
        current = self._current

        if current is next_state and not force:
            return False

        if current is not None:
            current.exit(next_state)
            self.state_exited.emit(self, current, next_state)

        self._previous = current
        self._current = next_state
        self._state_time = 0.0

        next_state.enter(current, payload)
        self.state_entered.emit(self, next_state, current, payload)
        self.state_changed.emit(self, current, next_state)
        return True

    def update(self, delta_time: float) -> None:
        if not self._running or self._paused or self._current is None:
            return

        delta = max(0.0, float(delta_time))
        self._state_time += delta

        self._updating = True
        try:
            current = self._current
            current.update(delta)
        finally:
            self._updating = False

        if self._flush_pending_change():
            return

        self._evaluate_transitions()

    def fixed_update(self, delta_time: float) -> None:
        if not self._running or self._paused or self._current is None:
            return

        delta = max(0.0, float(delta_time))

        self._updating = True
        try:
            current = self._current
            current.fixed_update(delta)
        finally:
            self._updating = False

        self._flush_pending_change()

    def _flush_pending_change(self) -> bool:
        pending = self._pending_change
        if pending is None:
            return False

        self._pending_change = None
        target, payload, force = pending
        return self._apply_change(target, payload, force)

    def _evaluate_transitions(self) -> bool:
        current = self._current
        if current is None:
            return False

        candidates = [
            transition
            for transition in self._transitions
            if transition.enabled
            and transition.target != current.name
            and transition.source in (self.ANY_STATE, current.name)
            and self._state_time >= transition.min_time
        ]
        candidates.sort(key=lambda item: (-item.priority, item.order))

        for transition in candidates:
            if not bool(transition.condition(self)):
                continue

            source_state = self._current
            changed = self._apply_change(
                transition.target,
                None,
                False,
            )
            if changed:
                self.transition_triggered.emit(
                    self,
                    transition,
                    source_state,
                    self._current,
                )
                return True

        return False

    def clear(self) -> None:
        self.stop()
        for state in self._states.values():
            state._unbind(self)
        self._states.clear()
        self._transitions.clear()
        self._transition_order = 0
