from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Transform:
    x: float = 0.0
    y: float = 0.0

    rotation: float = 0.0

    scale_x: float = 1.0
    scale_y: float = 1.0


@dataclass(slots=True)
class Velocity:
    x: float = 0.0
    y: float = 0.0


@dataclass(slots=True)
class Sprite:
    texture: object | None = None

    width: int = 32
    height: int = 32

    visible: bool = True


@dataclass(slots=True)
class Health:
    current: float = 100.0
    maximum: float = 100.0