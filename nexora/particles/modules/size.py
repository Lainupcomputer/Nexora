from __future__ import annotations

from dataclasses import dataclass
from random import Random

from nexora.particles.particle import Particle
from .base import ParticleModule, register_module


@register_module
@dataclass(slots=True)
class SizeOverLifetimeModule(ParticleModule):
    type_id = "size_over_lifetime"

    start_min: float = 4.0
    start_max: float = 4.0
    end_min: float = 0.0
    end_max: float = 0.0

    def initialize(self, particle: Particle, rng: Random) -> None:
        particle.start_size = rng.uniform(min(self.start_min, self.start_max), max(self.start_min, self.start_max))
        particle.end_size = rng.uniform(min(self.end_min, self.end_max), max(self.end_min, self.end_max))
        particle.size = particle.start_size

    def update(self, particle: Particle, delta_time: float) -> None:
        del delta_time
        t = particle.normalized_age
        particle.size = particle.start_size + (particle.end_size - particle.start_size) * t

    def to_state(self):
        return {
            "type": self.type_id,
            "start_min": float(self.start_min), "start_max": float(self.start_max),
            "end_min": float(self.end_min), "end_max": float(self.end_max),
        }

    @classmethod
    def from_state(cls, state):
        return cls(
            float(state.get("start_min", 4.0)), float(state.get("start_max", 4.0)),
            float(state.get("end_min", 0.0)), float(state.get("end_max", 0.0)),
        )
