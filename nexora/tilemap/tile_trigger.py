from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class TileTeleportEvent:
    """Information about one teleport trigger activation."""

    layer_name: str
    tile_x: int
    tile_y: int
    tile_id: int
    reference: str
    scene_name: str
    loading_scene: str
    actor: Any
