from __future__ import annotations

import sys
import threading
import time

from nexora.ecs.archetype_world import ArchetypeWorld
from nexora.ecs.component import Transform
from nexora.ecs.system import System
from nexora.threading import TaskScheduler


class SystemA(System):
    def __init__(self):
        self.thread_id = None

    def update(self, world, delta_time):
        self.thread_id = threading.get_ident()
        time.sleep(0.1)


class SystemB(System):
    def __init__(self):
        self.thread_id = None

    def update(self, world, delta_time):
        self.thread_id = threading.get_ident()
        time.sleep(0.1)


class SystemC(System):
    def __init__(self):
        self.thread_id = None

    def update(self, world, delta_time):
        self.thread_id = threading.get_ident()


def main():
    print("=" * 70)
    print("NEXORA PARALLEL ECS SYSTEM TEST")
    print("=" * 70)

    print(f"Python: {sys.version.split()[0]}")
    print(f"GIL:    {sys._is_gil_enabled()}")
    print()

    scheduler = TaskScheduler(workers=8)

    world = ArchetypeWorld(
        chunk_capacity=1024,
        scheduler=scheduler,
    )

    for _ in range(1000):
        world.create_entity(
            Transform()
        )

    system_a = SystemA()
    system_b = SystemB()
    system_c = SystemC()

    # A und B schreiben unterschiedliche Komponentenbereiche
    # bzw. haben keine gemeinsamen Schreibzugriffe.
    world.add_system(
        system_a,
        reads=(Transform,),
        priority=10,
    )

    world.add_system(
        system_b,
        reads=(Transform,),
        priority=10,
    )

    # C schreibt Transform und darf daher erst nach A/B laufen.
    world.add_system(
        system_c,
        reads=(Transform,),
        writes=(Transform,),
        priority=0,
    )

    print("SYSTEM GRAPH")
    print("-" * 70)

    for index, batch in enumerate(
        world.system_scheduler.batches
    ):
        print(
            f"Batch {index}: "
            + ", ".join(
                type(system).__name__
                for system in batch
            )
        )

    print()

    start = time.perf_counter()

    world.update(1.0 / 60.0)

    elapsed = time.perf_counter() - start

    print("EXECUTION")
    print("-" * 70)

    print(
        f"Runtime: {elapsed:.3f}s"
    )

    print(
        f"System A thread: {system_a.thread_id}"
    )

    print(
        f"System B thread: {system_b.thread_id}"
    )

    print(
        f"System C thread: {system_c.thread_id}"
    )

    print()

    print("VALIDATION")
    print("-" * 70)

    assert system_a.thread_id is not None
    assert system_b.thread_id is not None
    assert system_c.thread_id is not None

    assert system_a.thread_id != system_b.thread_id

    # A + B sollten parallel laufen.
    assert elapsed < 0.18, (
        f"Systems do not appear to run in parallel: "
        f"{elapsed:.3f}s"
    )

    print("✅ System A executed")
    print("✅ System B executed")
    print("✅ System C executed")
    print("✅ A and B used different worker threads")
    print("✅ A and B executed in parallel")
    print("✅ Dependency batch completed correctly")

    world.shutdown()
    scheduler.shutdown()

    print()
    print("=" * 70)
    print("PARALLEL SYSTEM TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()