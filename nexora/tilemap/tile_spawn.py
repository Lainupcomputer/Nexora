from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class TilePrefabSpawn:
    """Result of instantiating a prefab declared by TileMetadata.spawn."""

    layer_name: str
    tile_x: int
    tile_y: int
    tile_id: int
    prefab_source: str
    node: Any


@dataclass(slots=True, frozen=True)
class TileMetadataHit:
    """Resolved tile + metadata information for a map/world query."""

    layer_name: str
    tile_x: int
    tile_y: int
    tile_id: int
    metadata: Any
