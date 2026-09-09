from __future__ import annotations

import sys
import time

from nexora.ecs.archetype_world import ArchetypeWorld
from nexora.ecs.component import Transform, Velocity
from nexora.ecs.system import System
from nexora.threading import TaskScheduler


ENTITY_COUNT = 100_000
UPDATES = 60
WORKERS = 11

class MovementSystem(System):

    def __init__(self):
        self.calls = 0

    def update(self, world, delta_time):
        self.calls += 1

        start = time.perf_counter()

        world.parallel_query(
            (Transform, Velocity),
            self.update_chunk
        )

        elapsed = time.perf_counter() - start

        if self.calls <= 5:
            print(
                f"MovementSystem.update #{self.calls}: "
                f"{elapsed * 1000:.3f} ms"
            )

    @staticmethod
    def update_chunk(entities, transforms, velocities):
        for transform, velocity in zip(transforms, velocities):
            transform.x += velocity.x * (1.0 / 60.0)
            transform.y += velocity.y * (1.0 / 60.0)

class DebugSystem(System):
    def update(self, world, delta_time):
        pass


def create_world(scheduler):
    world = ArchetypeWorld(
        chunk_capacity=1024,
        scheduler=scheduler
    )

    for _ in range(ENTITY_COUNT):
        world.create_entity(
            Transform(),
            Velocity(x=1.0, y=0.5)
        )

    movement = MovementSystem()

    world.add_system(
        movement,
        reads=(Velocity,),
        writes=(Transform,),
        priority=10,
        main_thread_only=True
    )

    world.add_system(
        DebugSystem(),
        reads=(Transform,),
        priority=0,
        main_thread_only=True
    )

    return world, movement


def measure(name, function):
    start = time.perf_counter()

    for _ in range(UPDATES):
        function()

    runtime = time.perf_counter() - start

    print(
        f"{name:<35} "
        f"{runtime:.3f}s "
        f"({runtime / UPDATES:.6f}s/update)"
    )

    return runtime


def main():
    print("=" * 70)
    print("NEXORA ECS SCHEDULER PERFORMANCE DIAGNOSTIC")
    print("=" * 70)
    print()

    print(f"Python:   {sys.version.split()[0]}")
    print(f"GIL:      {sys._is_gil_enabled()}")
    print(f"Entities: {ENTITY_COUNT:,}")
    print(f"Workers:  {WORKERS}")
    print()

    scheduler = TaskScheduler(workers=WORKERS)

    world, movement = create_world(scheduler)

    print("SYSTEM GRAPH")
    print("-" * 70)

    print(f"Systems: {world.system_scheduler.system_count()}")
    print(f"Batches: {world.system_scheduler.batch_count()}")

    for index, batch in enumerate(world.system_scheduler.batches):
        print(
            f"Batch {index}: "
            + ", ".join(type(system).__name__ for system in batch)
        )

    print()
    print("PERFORMANCE")
    print("-" * 70)

    # 1. Vollständiger Scheduler-Pfad
    measure(
        "world.update()",
        lambda: world.update(1.0 / 60.0)
    )

    # 2. Nur das System direkt
    measure(
        "movement.update() direct",
        lambda: movement.update(world, 1.0 / 60.0)
    )

    # 3. Parallel Query direkt
    def direct_parallel_query():
        def update_chunk(entities, transforms, velocities):
            for transform, velocity in zip(transforms, velocities):
                transform.x += velocity.x * (1.0 / 60.0)
                transform.y += velocity.y * (1.0 / 60.0)

        world.parallel_query(
            (Transform, Velocity),
            update_chunk
        )

    measure(
        "world.parallel_query() direct",
        direct_parallel_query
    )

    print()
    print("VALIDATION")
    print("-" * 70)

    entity, transform, velocity = next(
        world.query(Transform, Velocity)
    )

    print(
        f"Position: "
        f"{transform.x:.6f} "
        f"{transform.y:.6f}"
    )

    print(
        f"Entities: "
        f"{'✅' if world.entity_count() == ENTITY_COUNT else '❌'}"
    )

    world.shutdown()
    scheduler.shutdown()

    print()
    print("=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()