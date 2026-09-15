from __future__ import annotations

from dataclasses import dataclass
from random import Random

from nexora.particles.particle import Particle
from .base import ParticleModule, register_module


@register_module
@dataclass(slots=True)
class RotationModule(ParticleModule):
    type_id = "rotation"

    min_rotation: float = 0.0
    max_rotation: float = 360.0
    min_angular_velocity: float = 0.0
    max_angular_velocity: float = 0.0

    def initialize(self, particle: Particle, rng: Random) -> None:
        particle.rotation = rng.uniform(min(self.min_rotation, self.max_rotation), max(self.min_rotation, self.max_rotation))
        particle.angular_velocity = rng.uniform(
            min(self.min_angular_velocity, self.max_angular_velocity),
            max(self.min_angular_velocity, self.max_angular_velocity),
        )

    def update(self, particle: Particle, delta_time: float) -> None:
        particle.rotation += particle.angular_velocity * delta_time

    def to_state(self):
        return {
            "type": self.type_id,
            "min_rotation": float(self.min_rotation), "max_rotation": float(self.max_rotation),
            "min_angular_velocity": float(self.min_angular_velocity),
            "max_angular_velocity": float(self.max_angular_velocity),
        }

    @classmethod
    def from_state(cls, state):
        return cls(
            float(state.get("min_rotation", 0.0)), float(state.get("max_rotation", 360.0)),
            float(state.get("min_angular_velocity", 0.0)), float(state.get("max_angular_velocity", 0.0)),
        )
