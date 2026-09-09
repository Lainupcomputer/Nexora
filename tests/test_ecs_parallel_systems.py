from __future__ import annotations

import time
import sys

from nexora.ecs.archetype_world import ArchetypeWorld
from nexora.ecs.system import System
from nexora.ecs.components import Transform, Velocity
from nexora.threading import TaskScheduler


# ============================================================
# SYSTEMS
# ============================================================

class MovementSystem(System):
    """
    Updates Transform from Velocity.
    """

    def update(
        self,
        world: ArchetypeWorld,
        delta_time: float,
    ) -> None:

        def update_chunk(
            entities,
            transforms,
            velocities,
        ):
            for i in range(len(entities)):
                transforms[i].x += (
                    velocities[i].x * delta_time
                )

                transforms[i].y += (
                    velocities[i].y * delta_time
                )

        world.parallel_query(
            (Transform, Velocity),
            update_chunk,
        )


class AISystem(System):
    """
    Dummy AI workload.

    Reads Transform and Velocity.
    Does not modify either component.
    """

    def update(
        self,
        world: ArchetypeWorld,
        delta_time: float,
    ) -> None:

        def update_chunk(
            entities,
            transforms,
            velocities,
        ):
            # Lightweight deterministic workload.
            # We intentionally don't modify ECS data here.
            for i in range(len(entities)):
                _ = (
                    transforms[i].x
                    + transforms[i].y
                    + velocities[i].x
                    + velocities[i].y
                )

        world.parallel_query(
            (Transform, Velocity),
            update_chunk,
        )


class ParticleSystem(System):
    """
    Dummy particle workload.

    Reads Transform and Velocity.
    Does not modify either component.
    """

    def update(
        self,
        world: ArchetypeWorld,
        delta_time: float,
    ) -> None:

        def update_chunk(
            entities,
            transforms,
            velocities,
        ):
            for i in range(len(entities)):
                _ = (
                    transforms[i].x * 0.5
                    + transforms[i].y * 0.5
                    + velocities[i].x
                    + velocities[i].y
                )

        world.parallel_query(
            (Transform, Velocity),
            update_chunk,
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("NEXORA PARALLEL SYSTEM ECS TEST")
    print("=" * 60)

    print()
    print(f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print("GIL:", "False" if sys._is_gil_enabled() is False else "True")

    ENTITY_COUNT = 100_000
    UPDATES = 60

    scheduler = TaskScheduler()

    print(f"Entities: {ENTITY_COUNT:,}")
    print(f"Workers: {scheduler.worker_count}")

    # ========================================================
    # WORLD
    # ========================================================

    world = ArchetypeWorld(
        chunk_capacity=1024,
        scheduler=scheduler,
    )

    # ========================================================
    # CREATE ENTITIES
    # ========================================================

    print()
    print("CREATING ENTITIES")
    print("-" * 60)

    start = time.perf_counter()

    for _ in range(ENTITY_COUNT):

        world.create_entity(
            Transform(
                x=0.0,
                y=0.0,
            ),
            Velocity(
                x=1.0,
                y=0.5,
            ),
        )

    creation_time = time.perf_counter() - start

    print(f"Creation: {creation_time:.3f}s")

    # ========================================================
    # SYSTEMS
    # ========================================================

    movement = world.add_system(
        MovementSystem(),
        reads=(Velocity,),
        writes=(Transform,),
        priority=100,
    )

    ai = world.add_system(
        AISystem(),
        reads=(Transform, Velocity),
        writes=(),
        priority=0,
    )

    particle = world.add_system(
        ParticleSystem(),
        reads=(Transform, Velocity),
        writes=(),
        priority=0,
    )

    # ========================================================
    # GRAPH
    # ========================================================

    print()
    print("SYSTEM GRAPH")
    print("-" * 60)

    print(
        f"Systems: {world.system_scheduler.system_count()}"
    )

    print(
        f"Batches: {world.system_scheduler.batch_count()}"
    )

    for index, batch in enumerate(
        world.system_scheduler.batches
    ):

        names = ", ".join(
            type(system).__name__
            for system in batch
        )

        print(
            f"Batch {index}: {names}"
        )

    # ========================================================
    # EXECUTION
    # ========================================================

    print()
    print("EXECUTION")
    print("-" * 60)

    start = time.perf_counter()

    for _ in range(UPDATES):

        world.update(
            1.0 / 60.0
        )

    execution_time = (
        time.perf_counter()
        - start
    )

    average = (
        execution_time
        / UPDATES
    )

    print(
        f"{UPDATES} updates: "
        f"{execution_time:.3f}s"
    )

    print(
        f"Average update: "
        f"{average:.6f}s"
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    print()
    print("VALIDATION")
    print("-" * 60)

    entity = next(
        world.query(
            Transform,
            Velocity,
        )
    )

    entity_id, transform, velocity = (
        entity[0],
        entity[1],
        entity[2],
    )

    expected_x = (
        1.0 * UPDATES / 60.0
    )

    expected_y = (
        0.5 * UPDATES / 60.0
    )

    print(
        f"Position: "
        f"{transform.x:.6f} "
        f"{transform.y:.6f}"
    )

    position_ok = (
        abs(transform.x - expected_x)
        < 1e-6
        and
        abs(transform.y - expected_y)
        < 1e-6
    )

    print(
        "Position:",
        "✅" if position_ok else "❌"
    )

    entity_count_ok = (
        world.entity_count()
        == ENTITY_COUNT
    )

    print(
        "Entities:",
        "✅" if entity_count_ok else "❌"
    )

    # ========================================================
    # RESULT
    # ========================================================

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)

    if position_ok and entity_count_ok:
        print(
            "Parallel system ECS test complete."
        )
    else:
        print(
            "Parallel system ECS test FAILED."
        )

    # ========================================================
    # SHUTDOWN
    # ========================================================

    world.shutdown()
    scheduler.shutdown()

    print()


if __name__ == "__main__":
    main()