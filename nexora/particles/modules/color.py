from __future__ import annotations

from dataclasses import dataclass
from random import Random

from nexora.particles.particle import Particle
from .base import ParticleModule, register_module


def _color(value):
    items = tuple(float(v) for v in value)
    if len(items) != 4:
        raise ValueError("Particle colors must contain RGBA values")
    return items


@register_module
@dataclass(slots=True)
class ColorOverLifetimeModule(ParticleModule):
    type_id = "color_over_lifetime"

    start_color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    end_color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 0.0)

    def initialize(self, particle: Particle, rng: Random) -> None:
        del rng
        particle.start_color = _color(self.start_color)
        particle.end_color = _color(self.end_color)
        particle.color = particle.start_color

    def update(self, particle: Particle, delta_time: float) -> None:
        del delta_time
        t = particle.normalized_age
        particle.color = tuple(a + (b - a) * t for a, b in zip(particle.start_color, particle.end_color))

    def to_state(self):
        return {"type": self.type_id, "start_color": tuple(self.start_color), "end_color": tuple(self.end_color)}

    @classmethod
    def from_state(cls, state):
        return cls(_color(state.get("start_color", (1, 1, 1, 1))), _color(state.get("end_color", (1, 1, 1, 0))))
