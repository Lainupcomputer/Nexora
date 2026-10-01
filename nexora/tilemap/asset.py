from __future__ import annotations

"""Portable TileMap authoring assets.

The ``.ntmap`` format is deliberately independent from ``.nxscene``.
It stores the tileset layout and the painted map layers, while a scene only
needs to reference the asset from its :class:`TileMapNode`.
"""

import json
from pathlib import Path
from typing import Any

from .tilemap import TileMap
from .tileset import TileSet


TILEMAP_ASSET_FORMAT = "nexora_tilemap"
TILEMAP_ASSET_VERSION = 1
TILEMAP_ASSET_SUFFIX = ".ntmap"


class TileMapAsset:
    """Serialized TileMap + TileSet data used by the editor and runtime."""

    def __init__(
        self,
        *,
        name: str,
        tilemap_state: dict[str, Any],
        tileset_state: dict[str, Any],
    ) -> None:
        self.name = str(name).strip() or "Untitled"
        self.tilemap_state = dict(tilemap_state)
        self.tileset_state = dict(tileset_state)

    @classmethod
    def from_components(cls, tilemap: TileMap, tileset: TileSet, *, name: str | None = None) -> "TileMapAsset":
        return cls(
            name=name or tilemap.name or tileset.name or "Untitled",
            tilemap_state=tilemap.to_state(),
            tileset_state=tileset.to_state(),
        )

    def build(self) -> tuple[TileMap, TileSet]:
        """Create independent runtime objects from the asset state."""
        return TileMap.from_state(dict(self.tilemap_state)), TileSet.from_state(dict(self.tileset_state))

    def to_state(self) -> dict[str, Any]:
        return {
            "format": TILEMAP_ASSET_FORMAT,
            "version": TILEMAP_ASSET_VERSION,
            "name": self.name,
            "tilemap": dict(self.tilemap_state),
            "tileset": dict(self.tileset_state),
        }

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "TileMapAsset":
        if not isinstance(state, dict) or state.get("format") != TILEMAP_ASSET_FORMAT:
            raise ValueError("Payload is not a Nexora TileMap asset.")
        version = int(state.get("version", 0))
        if version != TILEMAP_ASSET_VERSION:
            raise ValueError(f"Unsupported Nexora TileMap asset version: {version}")
        return cls(
            name=str(state.get("name", "Untitled")),
            tilemap_state=dict(state["tilemap"]),
            tileset_state=dict(state["tileset"]),
        )

    def save(self, path: str | Path) -> Path:
        path = Path(path).expanduser()
        if not str(path).lower().endswith(TILEMAP_ASSET_SUFFIX):
            path = Path(str(path) + TILEMAP_ASSET_SUFFIX)
        raw = json.dumps(self.to_state(), indent=2, sort_keys=True).encode("utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_bytes(raw)
        temporary.replace(path)
        return path.resolve()

    @classmethod
    def load(cls, path: str | Path) -> "TileMapAsset":
        path = Path(path).expanduser().resolve()
        state = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_state(state)


__all__ = [
    "TILEMAP_ASSET_FORMAT",
    "TILEMAP_ASSET_VERSION",
    "TILEMAP_ASSET_SUFFIX",
    "TileMapAsset",
]
