from __future__ import annotations

import sys
import threading
import time

from nexora.ecs import (
    World,
    ECSSystemScheduler,
    Transform,
    Velocity,
    System,
)


class AISystem(System):

    def update(self, world, dt):
        print(
            f"AI       | {threading.current_thread().name}"
        )

        time.sleep(0.05)


class ParticleSystem(System):

    def update(self, world, dt):
        print(
            f"Particles | {threading.current_thread().name}"
        )

        time.sleep(0.05)


class MovementSystem(System):

    def update(self, world, dt):
        print(
            f"Movement | {threading.current_thread().name}"
        )

        for entity, transform, velocity in world.query(
            Transform,
            Velocity,
        ):
            transform.x += velocity.x * dt
            transform.y += velocity.y * dt


def main():

    print("=" * 60)
    print("NEXORA PARALLEL ECS TEST")
    print("=" * 60)

    print()
    print("Python:", sys.version.split()[0])
    print("GIL:", sys._is_gil_enabled())

    world = World()

    scheduler = ECSSystemScheduler(
        world,
    )

    scheduler.add_system(
        AISystem(),
        reads={Transform},
        writes={Velocity},
    )

    scheduler.add_system(
        ParticleSystem(),
        reads={Transform},
        writes=set(),
    )

    scheduler.add_system(
        MovementSystem(),
        reads={Velocity},
        writes={Transform},
    )

    print()
    print("Systems:", scheduler.system_count())
    print("Batches:", scheduler.batch_count())

    print()
    print("Execution graph:")

    for index, batch in enumerate(
        scheduler.batches
    ):
        names = [
            type(system).__name__
            for system in batch
        ]

        print(
            f"  Batch {index}: "
            + ", ".join(names)
        )

    print()
    print("Running update...")
    print()

    start = time.perf_counter()

    scheduler.update(
        1.0 / 60.0
    )

    elapsed = time.perf_counter() - start

    print()
    print(
        f"Runtime: {elapsed:.3f}s"
    )

    print()

    if elapsed < 0.10:
        print(
            "Parallel execution: ✅"
        )
    else:
        print(
            "Parallel execution: ❌"
        )

    scheduler.shutdown()

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)
    print("Parallel ECS test complete.")


if __name__ == "__main__":
    main()