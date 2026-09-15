from __future__ import annotations

from .config import ParticleConfig
from .modules import (
    ColorOverLifetimeModule,
    GravityModule,
    LifetimeModule,
    RotationModule,
    SizeOverLifetimeModule,
    SpawnShapeModule,
    VelocityModule,
    BurstModule,
)


class ParticlePresets:
    @staticmethod
    def smoke() -> ParticleConfig:
        return ParticleConfig(
            max_particles=300,
            emission_rate=24.0,
            duration=2.0,
            looping=True,
            modules=[
                SpawnShapeModule(shape="circle", radius=6.0),
                LifetimeModule(1.5, 3.2),
                VelocityModule(-90.0, 35.0, 12.0, 32.0),
                SizeOverLifetimeModule(5.0, 10.0, 24.0, 42.0),
                ColorOverLifetimeModule((0.35, 0.35, 0.38, 0.7), (0.12, 0.12, 0.14, 0.0)),
                RotationModule(0.0, 360.0, -30.0, 30.0),
            ],
        )

    @staticmethod
    def sparks() -> ParticleConfig:
        return ParticleConfig(
            max_particles=128,
            emission_rate=0.0,
            duration=0.25,
            looping=False,
            one_shot=True,
            modules=[
                BurstModule(((0.0, 24),)),
                LifetimeModule(0.25, 0.8),
                VelocityModule(-90.0, 150.0, 90.0, 240.0),
                GravityModule(0.0, 180.0),
                SizeOverLifetimeModule(3.0, 5.0, 0.5, 1.0),
                ColorOverLifetimeModule((1.0, 0.72, 0.18, 1.0), (1.0, 0.15, 0.02, 0.0)),
            ],
        )

    @staticmethod
    def dust() -> ParticleConfig:
        return ParticleConfig(
            max_particles=160,
            emission_rate=0.0,
            duration=0.4,
            looping=False,
            one_shot=True,
            modules=[
                BurstModule(((0.0, 14),)),
                SpawnShapeModule(shape="circle", radius=7.0),
                LifetimeModule(0.45, 1.0),
                VelocityModule(-90.0, 170.0, 15.0, 55.0),
                SizeOverLifetimeModule(4.0, 8.0, 12.0, 20.0),
                ColorOverLifetimeModule((0.48, 0.40, 0.30, 0.55), (0.48, 0.40, 0.30, 0.0)),
            ],
        )
