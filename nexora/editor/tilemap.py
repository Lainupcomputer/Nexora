from __future__ import annotations

from collections.abc import Iterable

from nexora.editor.commands.tilemap_commands import (
    TileMapCellEdit,
    TileMapPaintCommand,
)
from nexora.tilemap import EMPTY_TILE


class TileMapEditorModel:
    """Editor-facing authoring model for a configured ``TileMapNode``.

    The model only creates commands; callers execute them on the editor's
    normal ``CommandStack``. This keeps painting, erasing and filling fully
    undoable without coupling the model to a particular UI.
    """

    def __init__(self, node) -> None:
        self.node = node
        self.active_layer_name: str | None = None
        self.selected_tile: int | None = None
        self._select_default_layer()

    @property
    def tilemap(self):
        tilemap = self.node.tilemap
        if tilemap is None:
            raise RuntimeError("TileMapNode has no TileMap.")
        return tilemap

    @property
    def tileset(self):
        return self.node.tileset

    @property
    def layer_names(self) -> tuple[str, ...]:
        return self.tilemap.layer_names

    @property
    def active_layer(self):
        if self.active_layer_name is None:
            raise RuntimeError("TileMap has no active layer.")
        return self.tilemap.require_layer(self.active_layer_name)

    def _select_default_layer(self) -> None:
        tilemap = self.node.tilemap
        if tilemap is not None and tilemap.layer_count:
            self.active_layer_name = tilemap.layer_names[0]

    def set_active_layer(self, layer_name: str) -> None:
        layer_name = str(layer_name)
        self.tilemap.require_layer(layer_name)
        self.active_layer_name = layer_name

    def set_selected_tile(self, tile_id: int | None) -> None:
        if tile_id is None:
            self.selected_tile = None
            return

        tile_id = int(tile_id)
        if tile_id < 0:
            raise ValueError("selected tile ID must be >= 0.")

        tileset = self.tileset
        if tileset is not None and not tileset.contains(tile_id):
            raise IndexError(f"Tile ID {tile_id} is outside the TileSet.")
        self.selected_tile = tile_id

    def cell_from_world(
        self,
        world_x: float,
        world_y: float,
    ) -> tuple[int, int] | None:
        """Return the map cell under a world point, or ``None`` outside."""

        x, y = self.node.world_to_tile(world_x, world_y)
        return (x, y) if self.tilemap.contains(x, y) else None

    def world_position_for_cell(
        self,
        x: int,
        y: int,
    ) -> tuple[float, float]:
        return self.node.tile_world_position(int(x), int(y))

    def _resolve_tile(self, tile_id: int | None) -> int:
        if tile_id is None:
            tile_id = self.selected_tile
        if tile_id is None:
            raise ValueError("No tile is selected for painting.")

        tile_id = int(tile_id)
        if tile_id < 0:
            raise ValueError("paint tile ID must be >= 0.")

        tileset = self.tileset
        if tileset is not None and not tileset.contains(tile_id):
            raise IndexError(f"Tile ID {tile_id} is outside the TileSet.")
        return tile_id

    def _make_command(
        self,
        cells: Iterable[tuple[int, int]],
        tile_id: int,
        *,
        label: str,
    ) -> TileMapPaintCommand:
        layer = self.active_layer
        edits: list[TileMapCellEdit] = []
        seen: set[tuple[int, int]] = set()

        for cell in cells:
            try:
                x, y = cell
            except (TypeError, ValueError) as exc:
                raise TypeError("Cells must be (x, y) pairs.") from exc

            x = int(x)
            y = int(y)
            if not self.tilemap.contains(x, y):
                continue
            if (x, y) in seen:
                continue
            seen.add((x, y))
            edits.append(
                TileMapCellEdit(
                    x,
                    y,
                    layer.get_tile(x, y),
                    tile_id,
                )
            )

        return TileMapPaintCommand(
            layer,
            edits,
            label=label,
        )

    def paint_command(
        self,
        cells: Iterable[tuple[int, int]],
        tile_id: int | None = None,
    ) -> TileMapPaintCommand:
        return self._make_command(
            cells,
            self._resolve_tile(tile_id),
            label="Paint Tiles",
        )

    def erase_command(
        self,
        cells: Iterable[tuple[int, int]],
    ) -> TileMapPaintCommand:
        return self._make_command(
            cells,
            EMPTY_TILE,
            label="Erase Tiles",
        )

    def fill_command(
        self,
        tile_id: int | None = None,
    ) -> TileMapPaintCommand:
        layer = self.active_layer
        cells = (
            (x, y)
            for y in range(self.tilemap.height)
            for x in range(self.tilemap.width)
        )
        return self._make_command(
            cells,
            self._resolve_tile(tile_id),
            label=f"Fill Layer {layer.name}",
        )
