from __future__ import annotations

from dataclasses import dataclass


Color3 = tuple[float, float, float]


@dataclass(slots=True, frozen=True)
class LightSnapshot:
    """Immutable per-frame light submitted to the renderer."""

    x: float
    y: float
    radius: float
    intensity: float
    color: Color3
    falloff: float
    mask: int = 0xFFFFFFFF

    cast_shadows: bool = False
    shadow_strength: float = 1.0
    shadow_softness: float = 0.0
    shadow_color: Color3 = (0.0, 0.0, 0.0)
    shadow_mask: int = 0xFFFFFFFF

    def __post_init__(self) -> None:
        if self.radius < 0.0:
            raise ValueError("Light radius cannot be negative")
        if self.intensity < 0.0:
            raise ValueError("Light intensity cannot be negative")
        if self.falloff <= 0.0:
            raise ValueError("Light falloff must be greater than zero")
        if len(self.color) != 3:
            raise ValueError("Light color must contain exactly three values")
        if not 0.0 <= self.shadow_strength <= 1.0:
            raise ValueError("Shadow strength must be between 0 and 1")
        if self.shadow_softness < 0.0:
            raise ValueError("Shadow softness cannot be negative")
        if len(self.shadow_color) != 3:
            raise ValueError("Shadow color must contain exactly three values")
