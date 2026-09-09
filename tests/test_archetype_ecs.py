from __future__ import annotations

import sys
import time

from nexora.ecs import (
    ArchetypeWorld,
    Transform,
    Velocity,
)


ENTITY_COUNT = 100_000
UPDATES = 60


def main():

    print("=" * 60)
    print("NEXORA ARCHETYPE ECS BENCHMARK")
    print("=" * 60)

    print()
    print("Python:", sys.version.split()[0])
    print("GIL:", sys._is_gil_enabled())
    print("Entities:", ENTITY_COUNT)
    print("Updates:", UPDATES)

    # ---------------------------------------------------------
    # CREATION
    # ---------------------------------------------------------

    world = ArchetypeWorld(
        chunk_capacity=1024
    )

    start = time.perf_counter()

    for index in range(
        ENTITY_COUNT
    ):

        world.create_entity(
            Transform(
                x=float(index),
                y=0.0,
            ),
            Velocity(
                x=1.0,
                y=0.5,
            ),
        )

    creation_time = (
        time.perf_counter()
        - start
    )

    print()
    print(
        f"Creation: {creation_time:.3f}s"
    )

    # ---------------------------------------------------------
    # STATISTICS
    # ---------------------------------------------------------

    print()
    print("WORLD")
    print("-" * 60)

    stats = world.statistics()

    for key, value in stats.items():
        print(
            f"{key}: {value}"
        )

    # ---------------------------------------------------------
    # QUERY
    # ---------------------------------------------------------

    start = time.perf_counter()

    count = 0

    for entity, transform, velocity in (
        world.query(
            Transform,
            Velocity,
        )
    ):

        transform.x += velocity.x
        transform.y += velocity.y

        count += 1

    query_time = (
        time.perf_counter()
        - start
    )

    print()
    print(
        f"Query entities: {count}"
    )

    print(
        f"Single query: {query_time:.6f}s"
    )

    # ---------------------------------------------------------
    # 60 UPDATES
    # ---------------------------------------------------------

    start = time.perf_counter()

    for _ in range(UPDATES):

        for (
            entity,
            transform,
            velocity,
        ) in world.query(
            Transform,
            Velocity,
        ):

            transform.x += (
                velocity.x
                * (1.0 / 60.0)
            )

            transform.y += (
                velocity.y
                * (1.0 / 60.0)
            )

    update_time = (
        time.perf_counter()
        - start
    )

    print()
    print(
        f"{UPDATES} updates: "
        f"{update_time:.3f}s"
    )

    print(
        f"Average update: "
        f"{update_time / UPDATES:.6f}s"
    )

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    first_entity = next(
        world.query(
            Transform,
            Velocity,
        )
    )

    entity, transform, velocity = (
        first_entity
    )

    print()
    print("VALIDATION")
    print("-" * 60)

    print(
        "First entity:",
        entity.id,
    )

    print(
        "Position:",
        transform.x,
        transform.y,
    )

    print(
        "Entity count:",
        world.entity_count(),
    )

    if count == ENTITY_COUNT:
        print(
            "Query count: ✅"
        )
    else:
        print(
            "Query count: ❌"
        )

    if world.entity_count() == ENTITY_COUNT:
        print(
            "Entity storage: ✅"
        )
    else:
        print(
            "Entity storage: ❌"
        )

    if world.chunk_count() > 1:
        print(
            "Chunk storage: ✅"
        )
    else:
        print(
            "Chunk storage: ❌"
        )

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)

    print(
        "Archetype ECS benchmark complete."
    )


if __name__ == "__main__":
    main()