from __future__ import annotations

import math

from nexora.ecs.world import World
from nexora.nodes import Node, ParticleEmitter2D
from nexora.particles import (
    BurstModule,
    ColorOverLifetimeModule,
    GravityModule,
    LifetimeModule,
    ParticleConfig,
    ParticlePresets,
    ParticleSystem,
    SizeOverLifetimeModule,
    SpawnShapeModule,
    VelocityModule,
)
from nexora.scene.serialization.registry import NodeFactoryRegistry


def make_emitter(config=None):
    world = World()
    parent = Node("Parent", world)
    emitter = ParticleEmitter2D("Particles", world)
    parent.add_child(emitter)
    if config is not None:
        emitter.config = config
    return world, parent, emitter


def test_config_round_trip_preserves_modules():
    config = ParticleConfig(
        max_particles=99,
        emission_rate=12.5,
        duration=2.0,
        looping=False,
        one_shot=True,
        local_space=False,
        layer=7,
        modules=[
            SpawnShapeModule(shape="circle", radius=8.0),
            LifetimeModule(0.5, 1.5),
            VelocityModule(-90.0, 40.0, 10.0, 20.0),
            GravityModule(0.0, 50.0),
            SizeOverLifetimeModule(2.0, 4.0, 8.0, 10.0),
            ColorOverLifetimeModule((1, 0, 0, 1), (0, 0, 0, 0)),
            BurstModule(((0.0, 5), (0.5, 2))),
        ],
    )
    restored = ParticleConfig.from_state(config.to_state())
    assert restored.max_particles == 99
    assert restored.local_space is False
    assert restored.layer == 7
    assert [type(m) for m in restored.modules] == [type(m) for m in config.modules]


def test_emitter_can_be_attached_to_node_and_emits_local_particles():
    config = ParticleConfig(max_particles=10, emission_rate=0.0, local_space=True, modules=[LifetimeModule(1.0, 1.0)])
    _, parent, emitter = make_emitter(config)
    parent.transform.x = 100.0
    emitter.transform.x = 20.0
    assert emitter.emit(3) == 3
    assert emitter.particle_count == 3
    assert emitter.world_position == (120.0, 0.0)
    assert all(p.x == 0.0 for p in emitter.particles)


def test_world_space_particles_do_not_follow_emitter_after_spawn():
    config = ParticleConfig(max_particles=10, emission_rate=0.0, local_space=False, modules=[LifetimeModule(1.0, 1.0)])
    _, parent, emitter = make_emitter(config)
    parent.transform.x = 50.0
    emitter.transform.x = 10.0
    emitter.emit(1)
    assert emitter.particles[0].x == 60.0
    parent.transform.x = 100.0
    assert emitter.particles[0].x == 60.0


def test_emission_rate_and_max_particles():
    config = ParticleConfig(max_particles=3, emission_rate=10.0, duration=10.0, modules=[LifetimeModule(5.0, 5.0)])
    _, _, emitter = make_emitter(config)
    emitter.play()
    emitter.update(0.5)
    assert emitter.particle_count == 3


def test_burst_one_shot_fires_once():
    config = ParticleConfig(
        max_particles=20,
        emission_rate=0.0,
        duration=0.2,
        looping=False,
        one_shot=True,
        modules=[BurstModule(((0.0, 7),)), LifetimeModule(1.0, 1.0)],
    )
    _, _, emitter = make_emitter(config)
    emitter.restart()
    assert emitter.particle_count == 7
    emitter.update(0.1)
    assert emitter.particle_count == 7


def test_gravity_and_size_update_particle():
    config = ParticleConfig(
        max_particles=4,
        emission_rate=0.0,
        modules=[
            LifetimeModule(2.0, 2.0),
            GravityModule(0.0, 100.0),
            SizeOverLifetimeModule(10.0, 10.0, 20.0, 20.0),
        ],
    )
    _, _, emitter = make_emitter(config)
    emitter.emit(1)
    emitter.update(1.0)
    particle = emitter.particles[0]
    assert particle.vy == 100.0
    assert particle.y == 100.0
    assert math.isclose(particle.size, 15.0)


def test_particle_system_tracks_emitters_and_counts():
    system = ParticleSystem()
    _, _, emitter = make_emitter(ParticleConfig(max_particles=10, emission_rate=0.0))
    system.register(emitter)
    emitter.emit(4)
    assert system.emitter_count == 1
    assert system.particle_count == 4
    system.stop_all(clear=True)
    assert system.particle_count == 0


def test_particle_emitter_serialization_round_trip():
    world, _, emitter = make_emitter(ParticlePresets.sparks())
    emitter.emitting = True
    registry = NodeFactoryRegistry()
    state = registry.dump_properties(emitter)
    restored = registry.create("ParticleEmitter2D", "Restored", world)
    registry.load_properties(restored, state)
    assert restored.emitting is True
    assert restored.config.one_shot is True
    assert restored.config.max_particles == emitter.config.max_particles
    assert [type(m) for m in restored.config.modules] == [type(m) for m in emitter.config.modules]
