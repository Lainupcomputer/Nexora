from __future__ import annotations

import math
from dataclasses import dataclass
from random import Random

from nexora.particles.particle import Particle
from .base import ParticleModule, register_module


@register_module
@dataclass(slots=True)
class SpawnShapeModule(ParticleModule):
    type_id = "spawn_shape"

    shape: str = "point"  # point | circle | box
    radius: float = 0.0
    width: float = 0.0
    height: float = 0.0
    edge_only: bool = False

    def initialize(self, particle: Particle, rng: Random) -> None:
        shape = self.shape.lower()
        if shape == "point":
            return
        if shape == "circle":
            angle = rng.random() * math.tau
            radius = max(float(self.radius), 0.0)
            if not self.edge_only:
                radius *= math.sqrt(rng.random())
            particle.x += math.cos(angle) * radius
            particle.y += math.sin(angle) * radius
            return
        if shape == "box":
            particle.x += rng.uniform(-self.width * 0.5, self.width * 0.5)
            particle.y += rng.uniform(-self.height * 0.5, self.height * 0.5)
            return
        raise ValueError(f"Unsupported particle spawn shape: {self.shape!r}")

    def to_state(self):
        return {
            "type": self.type_id,
            "shape": self.shape,
            "radius": float(self.radius),
            "width": float(self.width),
            "height": float(self.height),
            "edge_only": bool(self.edge_only),
        }

    @classmethod
    def from_state(cls, state):
        return cls(
            shape=str(state.get("shape", "point")),
            radius=float(state.get("radius", 0.0)),
            width=float(state.get("width", 0.0)),
            height=float(state.get("height", 0.0)),
            edge_only=bool(state.get("edge_only", False)),
        )
