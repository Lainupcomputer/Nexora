from __future__ import annotations

from dataclasses import dataclass
from random import Random

from nexora.particles.particle import Particle
from .base import ParticleModule, register_module


@register_module
@dataclass(slots=True)
class GravityModule(ParticleModule):
    type_id = "gravity"

    x: float = 0.0
    y: float = 98.0

    def initialize(self, particle: Particle, rng: Random) -> None:
        del particle, rng

    def update(self, particle: Particle, delta_time: float) -> None:
        particle.vx += self.x * delta_time
        particle.vy += self.y * delta_time

    def to_state(self):
        return {"type": self.type_id, "x": float(self.x), "y": float(self.y)}

    @classmethod
    def from_state(cls, state):
        return cls(float(state.get("x", 0.0)), float(state.get("y", 98.0)))
