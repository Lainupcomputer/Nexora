from __future__ import annotations

from nexora.ecs.world import World
from nexora.nodes.state import StateMachineNode
from nexora.state_machine import State, StateMachine


class RecordingState(State):
    def __init__(self, name: str, events: list) -> None:
        super().__init__(name)
        self.events = events
        self.updates = 0
        self.fixed_updates = 0

    def enter(self, previous, payload=None) -> None:
        self.events.append(("enter", self.name, None if previous is None else previous.name, payload))

    def exit(self, next_state) -> None:
        self.events.append(("exit", self.name, None if next_state is None else next_state.name))

    def update(self, delta_time: float) -> None:
        self.updates += 1

    def fixed_update(self, delta_time: float) -> None:
        self.fixed_updates += 1


def make_machine():
    events = []
    machine = StateMachine()
    idle = machine.add_state(RecordingState("idle", events))
    run = machine.add_state(RecordingState("run", events))
    attack = machine.add_state(RecordingState("attack", events))
    return machine, idle, run, attack, events


def test_start_enters_initial_state():
    machine, idle, _, _, events = make_machine()
    machine.start("idle", payload={"spawn": True})
    assert machine.current is idle
    assert machine.current_name == "idle"
    assert machine.state_time == 0.0
    assert events == [("enter", "idle", None, {"spawn": True})]


def test_change_state_runs_exit_then_enter():
    machine, idle, run, _, events = make_machine()
    machine.start("idle")
    events.clear()
    assert machine.change_state("run")
    assert machine.previous is idle
    assert machine.current is run
    assert events == [
        ("exit", "idle", "run"),
        ("enter", "run", "idle", None),
    ]


def test_same_state_is_ignored_without_force():
    machine, idle, _, _, events = make_machine()
    machine.start("idle")
    events.clear()
    assert not machine.change_state("idle")
    assert machine.current is idle
    assert events == []


def test_forced_reentry_runs_lifecycle():
    machine, idle, _, _, events = make_machine()
    machine.start("idle")
    events.clear()
    assert machine.change_state("idle", force=True)
    assert machine.current is idle
    assert events == [
        ("exit", "idle", "idle"),
        ("enter", "idle", "idle", None),
    ]


def test_update_tracks_state_time_and_updates_current():
    machine, idle, _, _, _ = make_machine()
    machine.start("idle")
    machine.update(0.25)
    machine.update(0.50)
    assert idle.updates == 2
    assert machine.state_time == 0.75


def test_transition_condition_changes_state():
    machine, _, run, _, _ = make_machine()
    machine.blackboard["moving"] = False
    machine.add_transition(
        "idle",
        "run",
        lambda sm: sm.blackboard["moving"],
    )
    machine.start("idle")
    machine.update(0.1)
    assert machine.current_name == "idle"
    machine.blackboard["moving"] = True
    machine.update(0.1)
    assert machine.current is run


def test_transition_min_time_is_respected():
    machine, _, run, _, _ = make_machine()
    machine.add_transition("idle", "run", lambda sm: True, min_time=1.0)
    machine.start("idle")
    machine.update(0.5)
    assert machine.current_name == "idle"
    machine.update(0.49)
    assert machine.current_name == "idle"
    machine.update(0.01)
    assert machine.current is run


def test_higher_priority_transition_wins():
    machine, _, run, attack, _ = make_machine()
    machine.add_transition("idle", "run", lambda sm: True, priority=1)
    machine.add_transition("idle", "attack", lambda sm: True, priority=10)
    machine.start("idle")
    machine.update(0.1)
    assert machine.current is attack
    assert machine.current is not run


def test_any_state_transition():
    machine, _, _, attack, _ = make_machine()
    machine.blackboard["attack"] = True
    machine.add_transition("*", "attack", lambda sm: sm.blackboard["attack"], priority=100)
    machine.start("run")
    machine.update(0.1)
    assert machine.current is attack


def test_change_requested_inside_update_is_deferred_safely():
    events = []
    machine = StateMachine()

    class ChangingState(RecordingState):
        def update(self, delta_time: float) -> None:
            super().update(delta_time)
            self.machine.change_state("next")

    first = machine.add_state(ChangingState("first", events))
    next_state = machine.add_state(RecordingState("next", events))
    machine.start("first")
    machine.update(0.1)
    assert first.updates == 1
    assert machine.current is next_state


def test_pause_blocks_updates_and_time():
    machine, idle, _, _, _ = make_machine()
    machine.start("idle")
    machine.pause()
    machine.update(1.0)
    assert idle.updates == 0
    assert machine.state_time == 0.0
    machine.resume()
    machine.update(0.5)
    assert idle.updates == 1
    assert machine.state_time == 0.5


def test_fixed_update_is_forwarded():
    machine, idle, _, _, _ = make_machine()
    machine.start("idle")
    machine.fixed_update(1 / 60)
    assert idle.fixed_updates == 1


def test_signals_fire_for_state_changes_and_transition():
    machine, _, _, _, _ = make_machine()
    changes = []
    transitions = []
    machine.state_changed.connect(
        lambda sm, old, new: changes.append((None if old is None else old.name, new.name))
    )
    machine.transition_triggered.connect(
        lambda sm, transition, old, new: transitions.append((transition.name, old.name, new.name))
    )
    machine.add_transition("idle", "run", lambda sm: True, name="start_running")
    machine.start("idle")
    machine.update(0.1)
    assert changes == [(None, "idle"), ("idle", "run")]
    assert transitions == [("start_running", "idle", "run")]


def test_state_machine_node_updates_machine():
    world = World()
    node = StateMachineNode("FSM", world)
    events = []
    idle = node.add_state(RecordingState("idle", events))
    node.start_state_machine("idle")
    node.update(0.2)
    node.fixed_update(1 / 60)
    assert idle.updates == 1
    assert idle.fixed_updates == 1
    node.destroy()
    assert not node.machine.running
