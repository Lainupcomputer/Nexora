from __future__ import annotations

import sys
import time

from nexora.ecs.archetype_world import ArchetypeWorld
from nexora.ecs.component import Transform, Velocity
from nexora.threading import TaskScheduler


ENTITY_COUNT = 100_000
UPDATES = 60
WORKERS = 11


def main():
    print("=" * 60)
    print("NEXORA DIRECT ARCHETYPE PARALLEL TEST")
    print("=" * 60)
    print()

    print(f"Python: {sys.version.split()[0]}")
    print(f"GIL: {sys._is_gil_enabled()}")
    print(f"Entities: {ENTITY_COUNT:,}")
    print(f"Workers: {WORKERS}")

    scheduler = TaskScheduler(workers=WORKERS)

    world = ArchetypeWorld(
        chunk_capacity=1024,
        scheduler=scheduler,
    )

    print()
    print("CREATING ENTITIES")
    print("-" * 60)

    start = time.perf_counter()

    for _ in range(ENTITY_COUNT):
        world.create_entity(
            Transform(),
            Velocity(x=1.0, y=0.5),
        )

    creation_time = time.perf_counter() - start

    print(f"Creation: {creation_time:.3f}s")

    print()
    print("WORLD")
    print("-" * 60)
    print(f"Entities: {world.entity_count():,}")
    print(f"Archetypes: {world.archetype_count()}")
    print(f"Chunks: {world.chunk_count()}")

    # ------------------------------------------------------------
    # DIRECT PARALLEL UPDATE
    # ------------------------------------------------------------

    def update_chunk(entities, transforms, velocities):
        for transform, velocity in zip(
            transforms,
            velocities,
        ):
            transform.x += velocity.x * (1.0 / 60.0)
            transform.y += velocity.y * (1.0 / 60.0)

    print()
    print("EXECUTION")
    print("-" * 60)

    start = time.perf_counter()

    for _ in range(UPDATES):
        world.parallel_query(
            (Transform, Velocity),
            update_chunk,
        )

    runtime = time.perf_counter() - start
    average = runtime / UPDATES

    print(f"{UPDATES} updates: {runtime:.3f}s")
    print(f"Average update: {average:.6f}s")

    # ------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------

    print()
    print("VALIDATION")
    print("-" * 60)

    entity, transform, velocity = next(
        world.query(
            Transform,
            Velocity,
        )
    )

    print(
        f"Position: "
        f"{transform.x:.6f} "
        f"{transform.y:.6f}"
    )

    expected_x = UPDATES / 60.0
    expected_y = (UPDATES / 60.0) * 0.5

    movement_valid = (
        abs(transform.x - expected_x) < 0.000001
        and
        abs(transform.y - expected_y) < 0.000001
    )

    entities_valid = (
        world.entity_count() == ENTITY_COUNT
    )

    print(
        "Movement:",
        "✅" if movement_valid else "❌",
    )

    print(
        "Entities:",
        "✅" if entities_valid else "❌",
    )

    # ------------------------------------------------------------
    # CLEANUP
    # ------------------------------------------------------------

    world.shutdown()
    scheduler.shutdown()

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)

    if movement_valid and entities_valid:
        print("Direct parallel archetype test complete.")
    else:
        print("❌ VALIDATION FAILED")


if __name__ == "__main__":
    main()