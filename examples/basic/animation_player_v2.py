from __future__ import annotations

from nexora.animation import (
    AnimationClip,
    AnimationEvent,
    AnimationPlayer,
    AnimationStateMachine,
)
from nexora.ecs.world import World


def main() -> None:
    world = World()
    player = AnimationPlayer("PlayerAnimation", world)

    idle = AnimationClip.from_row(
        "idle", row=0, frame_count=4, columns=8, rows=2, fps=6.0, loop=True
    )
    attack = AnimationClip.from_row(
        "attack",
        row=1,
        frame_count=8,
        columns=8,
        rows=2,
        fps=12.0,
        loop=False,
        events=(AnimationEvent(4, "hit", {"damage": 20}),),
    )

    player.add_animation(idle)
    player.add_animation(attack)

    player.animation_started.connect(lambda name: print("started:", name))
    player.frame_changed.connect(lambda frame, index: print("frame:", index, frame.index))
    player.event.connect(lambda event: print("event:", event.name, event.data))
    player.finished.connect(lambda name: print("finished:", name))

    machine = AnimationStateMachine(player)
    machine.add_state("idle", "idle")
    machine.add_state("attack", "attack")

    attacking = {"value": False}
    machine.add_transition(
        "idle", "attack", lambda: attacking["value"], priority=10
    )
    machine.add_transition(
        "attack",
        "idle",
        lambda: player.animation_finished,
    )

    machine.set_state("idle")
    player.update(0.2)

    attacking["value"] = True
    machine.update()
    attacking["value"] = False

    for _ in range(12):
        player.update(1.0 / 12.0)
        machine.update()


if __name__ == "__main__":
    main()
