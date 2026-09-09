from __future__ import annotations

import sys
import threading
import time

from nexora.ecs import (
    World,
    System,
    ECSSystemScheduler,
    ECSDependencyCycleError,
    Transform,
    Velocity,
)


class InputSystem(System):

    def update(self, world, dt):
        print(
            "Input    |",
            threading.current_thread().name,
        )
        time.sleep(0.03)


class AISystem(System):

    def update(self, world, dt):
        print(
            "AI       |",
            threading.current_thread().name,
        )
        time.sleep(0.05)


class ParticleSystem(System):

    def update(self, world, dt):
        print(
            "Particles|",
            threading.current_thread().name,
        )
        time.sleep(0.05)


class PhysicsSystem(System):

    def update(self, world, dt):
        print(
            "Physics  |",
            threading.current_thread().name,
        )
        time.sleep(0.05)


class MovementSystem(System):

    def update(self, world, dt):
        print(
            "Movement |",
            threading.current_thread().name,
        )

        for (
            entity,
            transform,
            velocity,
        ) in world.query(
            Transform,
            Velocity,
        ):
            transform.x += velocity.x * dt


class RenderPrepSystem(System):

    def update(self, world, dt):
        print(
            "RenderPrep|",
            threading.current_thread().name,
        )
        time.sleep(0.03)


def test_normal_graph():

    world = World()

    scheduler = ECSSystemScheduler(
        world,
    )

    input_system = scheduler.add_system(
        InputSystem(),
        priority=100,
    )

    ai_system = scheduler.add_system(
        AISystem(),
        reads={Transform},
        writes={Velocity},
        priority=200,
        depends_on={input_system},
    )

    particles = scheduler.add_system(
        ParticleSystem(),
        reads={Transform},
        priority=200,
    )

    physics = scheduler.add_system(
        PhysicsSystem(),
        reads={Transform, Velocity},
        writes={Velocity},
        priority=300,
    )

    movement = scheduler.add_system(
        MovementSystem(),
        reads={Velocity},
        writes={Transform},
        priority=400,
    )

    render_prep = scheduler.add_system(
        RenderPrepSystem(),
        reads={Transform},
        priority=500,
    )

    print()
    print("SYSTEM GRAPH")
    print("-" * 60)

    for index, batch in enumerate(
        scheduler.batches
    ):

        names = [
            type(system).__name__
            for system in batch
        ]

        print(
            f"Batch {index}: "
            + ", ".join(names)
        )

    print()
    print("DEPENDENCIES")
    print("-" * 60)

    for source, targets in (
        scheduler.dependencies().items()
    ):

        if targets:
            print(
                f"{source} -> "
                + ", ".join(targets)
            )

    print()
    print("EXECUTION")
    print("-" * 60)

    start = time.perf_counter()

    scheduler.update(
        1.0 / 60.0
    )

    elapsed = (
        time.perf_counter()
        - start
    )

    print()
    print(
        f"Runtime: {elapsed:.3f}s"
    )

    print()
    print(
        "Systems:",
        scheduler.system_count(),
    )

    print(
        "Batches:",
        scheduler.batch_count(),
    )

    scheduler.shutdown()

    return elapsed


def test_cycle_detection():

    world = World()

    scheduler = ECSSystemScheduler(
        world,
    )

    a = scheduler.add_system(
        InputSystem()
    )

    b = scheduler.add_system(
        AISystem(),
        depends_on={a},
    )

    try:

        scheduler.add_system(
            ParticleSystem(),
            depends_on={b},
        )

        # Create a cycle manually for testing.
        scheduler._access[a].depends_on = frozenset(
            {scheduler.systems[2]}
        )

        scheduler._dirty = True
        scheduler._rebuild()

    except ECSDependencyCycleError:

        print(
            "Cycle detection: ✅"
        )

    else:

        print(
            "Cycle detection: ❌"
        )

    scheduler.shutdown()


def main():

    print("=" * 60)
    print("NEXORA ECS DEPENDENCY GRAPH TEST")
    print("=" * 60)

    print()
    print("Python:", sys.version.split()[0])
    print("GIL:", sys._is_gil_enabled())

    elapsed = test_normal_graph()

    print()
    print(
        "Parallel graph execution:",
        "✅" if elapsed < 0.30 else "❌",
    )

    print()
    test_cycle_detection()

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)
    print("ECS dependency graph test complete.")


if __name__ == "__main__":
    main()