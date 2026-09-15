from __future__ import annotations

import math
from dataclasses import dataclass
from random import Random

from nexora.particles.particle import Particle
from .base import ParticleModule, register_module


@register_module
@dataclass(slots=True)
class VelocityModule(ParticleModule):
    type_id = "velocity"

    direction_degrees: float = -90.0
    spread_degrees: float = 360.0
    min_speed: float = 20.0
    max_speed: float = 60.0

    def initialize(self, particle: Particle, rng: Random) -> None:
        half = self.spread_degrees * 0.5
        angle = math.radians(rng.uniform(self.direction_degrees - half, self.direction_degrees + half))
        speed = rng.uniform(min(self.min_speed, self.max_speed), max(self.min_speed, self.max_speed))
        particle.vx += math.cos(angle) * speed
        particle.vy += math.sin(angle) * speed

    def to_state(self):
        return {
            "type": self.type_id,
            "direction_degrees": float(self.direction_degrees),
            "spread_degrees": float(self.spread_degrees),
            "min_speed": float(self.min_speed),
            "max_speed": float(self.max_speed),
        }

    @classmethod
    def from_state(cls, state):
        return cls(
            float(state.get("direction_degrees", -90.0)),
            float(state.get("spread_degrees", 360.0)),
            float(state.get("min_speed", 20.0)),
            float(state.get("max_speed", 60.0)),
        )
