from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexora.nodes.node import Node

Color = tuple[float, float, float]


@dataclass(slots=True)
class CameraStep:
    """Internal cinematic sequence step."""

    kind: str
    duration: float = 0.0
    x: float | None = None
    y: float | None = None
    zoom: float | None = None
    target: Node | None = None
    color: Color | None = None
    alpha: float | None = None
    size: float | None = None
    easing: str = "ease_in_out"
    elapsed: float = 0.0
    started: bool = False
    start_x: float = 0.0
    start_y: float = 0.0
    start_zoom: float = 1.0


# Backwards-compatible private name used by older internal extensions.
_CameraStep = CameraStep
