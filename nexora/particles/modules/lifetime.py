from __future__ import annotations

from dataclasses import dataclass
from random import Random

from nexora.particles.particle import Particle
from .base import ParticleModule, register_module


@register_module
@dataclass(slots=True)
class LifetimeModule(ParticleModule):
    type_id = "lifetime"

    minimum: float = 1.0
    maximum: float = 1.0

    def initialize(self, particle: Particle, rng: Random) -> None:
        low = max(min(self.minimum, self.maximum), 0.000001)
        high = max(max(self.minimum, self.maximum), low)
        particle.lifetime = rng.uniform(low, high)

    def to_state(self):
        return {"type": self.type_id, "minimum": float(self.minimum), "maximum": float(self.maximum)}

    @classmethod
    def from_state(cls, state):
        return cls(float(state.get("minimum", 1.0)), float(state.get("maximum", 1.0)))
