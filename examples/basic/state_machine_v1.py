from __future__ import annotations

from nexora.core.game import Game
from nexora.nodes import StateMachineNode
from nexora.scene import Scene
from nexora.state_machine import State


class DemoState(State):
    def enter(self, previous, payload=None) -> None:
        previous_name = previous.name if previous is not None else "None"
        print(f"[FSM] enter {self.name} (from {previous_name})")

    def exit(self, next_state) -> None:
        next_name = next_state.name if next_state is not None else "None"
        print(f"[FSM] exit  {self.name} (to {next_name})")


class StateMachineExample(Game):
    def __init__(self) -> None:
        super().__init__(
            project_name="StateMachineExample",
            title="Nexora - Gameplay State Machine V1",
            width=1280,
            height=720,
            target_fps=60,
            resizable=True,
            vsync=True,
        )
        self.fsm: StateMachineNode | None = None

    def initialize(self) -> None:
        self.scene = Scene("StateMachineExample")

        self.input.bind("exit", "ESCAPE")
        self.input.bind("toggle_move", "SPACE")
        self.input.bind("attack", "A")
        self.input.bind("toggle_fsm", "P")

        self.fsm = StateMachineNode("PlayerFSM", self.scene.world)
        self.scene.root.add_child(self.fsm)

        self.fsm.add_state(DemoState("idle"))
        self.fsm.add_state(DemoState("run"))
        self.fsm.add_state(DemoState("attack"))

        board = self.fsm.machine.blackboard
        board["moving"] = False
        board["attack"] = False

        self.fsm.add_transition(
            "idle",
            "run",
            lambda sm: bool(sm.blackboard["moving"]),
        )
        self.fsm.add_transition(
            "run",
            "idle",
            lambda sm: not bool(sm.blackboard["moving"]),
        )
        self.fsm.add_transition(
            "*",
            "attack",
            lambda sm: bool(sm.blackboard["attack"]),
            priority=100,
        )
        self.fsm.add_transition(
            "attack",
            "run",
            lambda sm: sm.state_time >= 0.75 and bool(sm.blackboard["moving"]),
            priority=10,
        )
        self.fsm.add_transition(
            "attack",
            "idle",
            lambda sm: sm.state_time >= 0.75 and not bool(sm.blackboard["moving"]),
        )

        self.fsm.machine.state_changed.connect(self._on_state_changed)
        self.fsm.start_state_machine("idle")

        print("=" * 60)
        print(" Nexora Gameplay State Machine V1")
        print("=" * 60)
        print("SPACE -> toggle idle/run")
        print("A     -> attack for 0.75 seconds")
        print("P     -> pause/resume state machine")
        print("ESC   -> exit")
        print()

    def _on_state_changed(self, machine, old, new) -> None:
        old_name = old.name if old is not None else "None"
        print(f"[FSM] changed {old_name} -> {new.name}")

    def update(self, delta_time: float) -> None:
        if self.input.action("exit").pressed:
            self.stop()
            return

        fsm = self.fsm
        if fsm is not None:
            board = fsm.machine.blackboard

            if self.input.action("toggle_move").pressed:
                board["moving"] = not bool(board["moving"])
                print(f"[FSM] moving={board['moving']}")

            if self.input.action("attack").pressed:
                board["attack"] = True
                fsm.change_state("attack", force=True)
                board["attack"] = False

            if self.input.action("toggle_fsm").pressed:
                if fsm.machine.paused:
                    fsm.machine.resume()
                    print("[FSM] resumed")
                else:
                    fsm.machine.pause()
                    print("[FSM] paused")

        super().update(delta_time)


if __name__ == "__main__":
    StateMachineExample().run()
