from __future__ import annotations

import sys

from nexora.ecs.archetype_world import ArchetypeWorld
from nexora.ecs.component import Health, Transform, Velocity
from nexora.ecs.system import System
from nexora.threading import TaskScheduler


class SpawnSystem(System):
    def update(self, world, delta_time):
        commands = world.commands()

        for _ in range(100):
            commands.create(
                Transform(),
                Velocity(x=10, y=0),
                Health(),
            )


class DamageSystem(System):
    def update(self, world, delta_time):
        for entity, health in world.query(Health):
            health.current -= 200


class DestroySystem(System):
    def update(self, world, delta_time):
        commands = world.commands()

        for entity, health in world.query(Health):
            if health.current <= 0:
                commands.destroy(entity)


def main():
    print("=" * 70)
    print("NEXORA ECS COMMAND BUFFER TEST")
    print("=" * 70)

    print(f"Python: {sys.version.split()[0]}")
    print(f"GIL:    {sys._is_gil_enabled()}")
    print()

    scheduler = TaskScheduler(workers=8)

    world = ArchetypeWorld(
        chunk_capacity=128,
        scheduler=scheduler,
    )

    # ==============================================================
    # 1. SPAWN
    # ==============================================================

    print("1. SPAWN")
    print("-" * 70)

    spawn_system = SpawnSystem()

    world.add_system(
        spawn_system,
        priority=10,
    )

    world.update(1.0 / 60.0)

    assert world.entity_count() == 100

    print("✅ 100 entities created through CommandBuffer")

    # Spawn-System entfernen, damit es bei den nächsten Updates
    # nicht erneut 100 Entities erzeugt.
    world.remove_system(spawn_system)

    # ==============================================================
    # 2. DAMAGE
    # ==============================================================

    print()
    print("2. DAMAGE")
    print("-" * 70)

    damage_system = DamageSystem()

    world.add_system(
        damage_system,
        reads=(Health,),
        writes=(Health,),
        priority=10,
    )

    world.update(1.0 / 60.0)

    dead_count = 0

    for entity, health in world.query(Health):
        if health.current <= 0:
            dead_count += 1

    assert world.entity_count() == 100
    assert dead_count == 100

    print("✅ Damage system modified all 100 Health components")
    print("✅ All 100 entities are dead")

    # Damage-System entfernen.
    world.remove_system(damage_system)

    # ==============================================================
    # 3. DESTROY
    # ==============================================================

    print()
    print("3. DESTROY")
    print("-" * 70)

    destroy_system = DestroySystem()

    world.add_system(
        destroy_system,
        reads=(Health,),
        priority=10,
    )

    world.update(1.0 / 60.0)

    assert world.entity_count() == 0

    print("✅ All dead entities destroyed")
    print("✅ Structural changes applied through CommandBuffer")

    # ==============================================================
    # SHUTDOWN
    # ==============================================================

    world.shutdown()
    scheduler.shutdown()

    print()
    print("=" * 70)
    print("COMMAND BUFFER TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()