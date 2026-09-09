from __future__ import annotations

import sys
import time

from nexora.ecs.archetype_world import ArchetypeWorld
from nexora.ecs.component import Transform, Velocity
from nexora.threading import TaskScheduler


ENTITY_COUNTS = (
    100_000,
    250_000,
    500_000,
    1_000_000,
)

UPDATES = 60
CHUNK_CAPACITY = 1024
WORKERS = 11


def run_benchmark(entity_count: int, scheduler: TaskScheduler):

    print()
    print("=" * 60)
    print(f"TEST: {entity_count:,} ENTITIES")
    print("=" * 60)

    world = ArchetypeWorld(
        chunk_capacity=CHUNK_CAPACITY,
        scheduler=scheduler,
    )

    print("Creating entities...")

    start = time.perf_counter()

    for _ in range(entity_count):
        world.create_entity(
            Transform(),
            Velocity(
                x=1.0,
                y=0.5,
            ),
        )

    creation_time = time.perf_counter() - start

    stats = world.statistics()

    print(f"Creation: {creation_time:.3f}s")
    print()
    print("WORLD")
    print("-" * 60)
    print(f"entities: {stats['entities']}")
    print(f"archetypes: {stats['archetypes']}")
    print(f"chunks: {stats['chunks']}")
    print(f"chunk_capacity: {stats['chunk_capacity']}")

    def update_chunk(
        entities,
        transforms,
        velocities,
    ):
        for transform, velocity in zip(
            transforms,
            velocities,
        ):
            transform.x += velocity.x
            transform.y += velocity.y

    print()
    print("PARALLEL UPDATE")
    print("-" * 60)

    start = time.perf_counter()

    for _ in range(UPDATES):
        world.parallel_query(
            (Transform, Velocity),
            update_chunk,
        )

    update_time = time.perf_counter() - start
    average = update_time / UPDATES

    entity = next(
        world.query(Transform, Velocity)
    )

    _, transform, _ = entity

    print(f"{UPDATES} updates: {update_time:.3f}s")
    print(f"Average update: {average:.6f}s")

    print()
    print("VALIDATION")
    print("-" * 60)

    expected_x = float(UPDATES)
    expected_y = float(UPDATES) * 0.5

    print(
        f"First entity position: "
        f"{transform.x:.6f} "
        f"{transform.y:.6f}"
    )

    print(
        "Position:",
        "✅"
        if (
            abs(transform.x - expected_x) < 0.000001
            and abs(transform.y - expected_y) < 0.000001
        )
        else "❌",
    )

    print(
        "Entity count:",
        "✅"
        if world.entity_count() == entity_count
        else "❌",
    )

    return {
        "entities": entity_count,
        "chunks": stats["chunks"],
        "creation": creation_time,
        "updates": update_time,
        "average": average,
    }


def main():

    print("=" * 60)
    print("NEXORA ECS SCALING BENCHMARK")
    print("=" * 60)

    print()
    print(f"Python: {sys.version.split()[0]}")
    print(f"GIL: {sys._is_gil_enabled()}")
    print(f"Workers: {WORKERS}")
    print(f"Updates per test: {UPDATES}")
    print(f"Chunk capacity: {CHUNK_CAPACITY}")

    scheduler = TaskScheduler(
        workers=WORKERS
    )

    results = []

    try:
        for entity_count in ENTITY_COUNTS:

            result = run_benchmark(
                entity_count,
                scheduler,
            )

            results.append(result)

    finally:
        scheduler.shutdown()

    print()
    print("=" * 60)
    print("SCALING RESULTS")
    print("=" * 60)

    print(
        f"{'Entities':>12} "
        f"{'Chunks':>8} "
        f"{'Creation':>12} "
        f"{'60 Updates':>12} "
        f"{'Avg Update':>12}"
    )

    print("-" * 60)

    for result in results:

        print(
            f"{result['entities']:>12,} "
            f"{result['chunks']:>8,} "
            f"{result['creation']:>11.3f}s "
            f"{result['updates']:>11.3f}s "
            f"{result['average']:>11.6f}s"
        )

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)
    print("ECS scaling benchmark complete.")


if __name__ == "__main__":
    main()