from __future__ import annotations

from dataclasses import dataclass


Color = tuple[float, float, float, float]


@dataclass(slots=True)
class Particle:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    age: float = 0.0
    lifetime: float = 1.0
    size: float = 4.0
    start_size: float = 4.0
    end_size: float = 4.0
    color: Color = (1.0, 1.0, 1.0, 1.0)
    start_color: Color = (1.0, 1.0, 1.0, 1.0)
    end_color: Color = (1.0, 1.0, 1.0, 0.0)
    rotation: float = 0.0
    angular_velocity: float = 0.0

    @property
    def normalized_age(self) -> float:
        if self.lifetime <= 0.0:
            return 1.0
        return max(0.0, min(self.age / self.lifetime, 1.0))

    @property
    def alive(self) -> bool:
        return self.age < self.lifetime
