from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from nexora.tilemap import EMPTY_TILE, TileProjection
from nexora.tilemap.tile_layer import normalize_layer_role


@dataclass(frozen=True, slots=True)
class TileMapCellEdit:
    """The before/after value of one edited tile cell."""

    x: int
    y: int
    before: int
    after: int


class TileMapAssetCommand:
    """Undoable assignment of a portable ``.ntmap`` asset."""

    def __init__(self, node, asset_path: str, assets) -> None:
        self.node = node
        self.asset_path = str(asset_path).replace("\\", "/")
        self.assets = assets
        self.previous_asset = node.tilemap_asset
        self.previous_tilemap = node.tilemap
        self.previous_tileset = node.tileset
        self.previous_texture = node.texture
        self.label = f"Assign TileMap Asset: {self.asset_path}"

    def execute(self):
        self.node.load_tilemap_asset(self.asset_path, self.assets)
        return self.node

    def undo(self):
        if self.previous_tilemap is None or self.previous_tileset is None:
            self.node.tilemap = self.previous_tilemap
            self.node.tileset = self.previous_tileset
            self.node.texture = self.previous_texture
            self.node.tilemap_asset = self.previous_asset
            clear_caches = getattr(self.node, "clear_chunk_caches", None)
            if callable(clear_caches):
                clear_caches()
        else:
            self.node.set_map(
                self.previous_tilemap,
                self.previous_tileset,
                self.previous_texture,
            )
            self.node.tilemap_asset = self.previous_asset
        return self.node


class TileMapPaintCommand:
    """Undoable batch edit for one TileLayer.

    A drag or fill operation is represented by one command. Repeated cells
    are coalesced so a cell touched several times during a drag still has a
    single, predictable before/after pair.
    """

    def __init__(
        self,
        layer,
        edits: Iterable[TileMapCellEdit],
        *,
        label: str = "Paint Tiles",
    ) -> None:
        self.layer = layer
        self.edits = self._normalize_edits(layer, edits)
        self.label = str(label)

    @staticmethod
    def _normalize_edits(
        layer,
        edits: Iterable[TileMapCellEdit],
    ) -> tuple[TileMapCellEdit, ...]:
        normalized: dict[tuple[int, int], TileMapCellEdit] = {}

        for edit in edits:
            if not isinstance(edit, TileMapCellEdit):
                try:
                    edit = TileMapCellEdit(*edit)
                except (TypeError, ValueError) as exc:
                    raise TypeError(
                        "Tile edits must be TileMapCellEdit instances "
                        "or (x, y, before, after) tuples."
                    ) from exc

            x = int(edit.x)
            y = int(edit.y)
            if not layer.contains(x, y):
                raise IndexError(
                    f"Tile coordinate ({x}, {y}) is outside layer "
                    f"{layer.name!r}."
                )

            before = int(edit.before)
            after = int(edit.after)
            if before < EMPTY_TILE or after < EMPTY_TILE:
                raise ValueError("Tile IDs must be >= -1.")

            key = (x, y)
            previous = normalized.get(key)
            if previous is None:
                normalized[key] = TileMapCellEdit(
                    x,
                    y,
                    before,
                    after,
                )
            else:
                normalized[key] = TileMapCellEdit(
                    x,
                    y,
                    previous.before,
                    after,
                )

        return tuple(
            edit
            for edit in normalized.values()
            if edit.before != edit.after
        )

    @staticmethod
    def _set_tile(layer, x: int, y: int, tile_id: int) -> None:
        if tile_id == EMPTY_TILE:
            layer.clear_tile(x, y)
        else:
            layer.set_tile(x, y, tile_id)

    def _apply(self, *, use_after: bool):
        for edit in self.edits:
            tile_id = edit.after if use_after else edit.before
            self._set_tile(
                self.layer,
                edit.x,
                edit.y,
                tile_id,
            )
        # Keep the selected TileMapNode selected in the editor's generic
        # undo/redo handler.
        return None

    def execute(self):
        return self._apply(use_after=True)

    def undo(self):
        return self._apply(use_after=False)


class TileMapProjectionCommand:
    """Undoable projection switch without changing cell data."""

    def __init__(self, node, projection: TileProjection | str) -> None:
        if node.tilemap is None:
            raise RuntimeError("TileMapNode has no TileMap.")
        self.node = node
        self.old_projection = node.tilemap.projection
        self.new_projection = TileProjection.coerce(projection)
        self.label = f"Set TileMap Projection: {self.new_projection.value}"

    def _apply(self, projection: TileProjection):
        self.node.tilemap.projection = projection
        clear_caches = getattr(self.node, "clear_chunk_caches", None)
        if callable(clear_caches):
            clear_caches()
        return self.node

    def execute(self):
        return self._apply(self.new_projection)

    def undo(self):
        return self._apply(self.old_projection)


class TileMapLayerAddCommand:
    """Undoable creation of a layer in a TileMap asset."""

    def __init__(self, tilemap, name: str) -> None:
        self.tilemap = tilemap
        self.name = str(name).strip()
        if not self.name:
            raise ValueError("Layer name cannot be empty.")
        self.layer = None
        self.label = f"Add Layer: {self.name}"

    def execute(self):
        self.layer = self.tilemap.create_layer(self.name)
        return self.layer

    def undo(self):
        if self.layer is not None:
            self.tilemap.remove_layer(self.layer)
        return self.layer


class TileMapLayerRemoveCommand:
    """Undoable removal of a layer, retaining its painted cells."""

    def __init__(self, tilemap, name: str) -> None:
        self.tilemap = tilemap
        self.name = str(name)
        self.layer = tilemap.require_layer(self.name)
        self.index = tilemap.layer_index(self.name)
        self.label = f"Remove Layer: {self.name}"

    def execute(self):
        self.tilemap.remove_layer(self.layer)
        return self.layer

    def undo(self):
        self.tilemap.add_layer(self.layer, index=self.index)
        return self.layer


class TileMapLayerRenameCommand:
    """Undoable layer rename that keeps TileMap lookup indexes valid."""

    def __init__(self, tilemap, layer, new_name: str) -> None:
        self.tilemap = tilemap
        self.layer = layer
        self.old_name = str(layer.name)
        self.new_name = str(new_name).strip()
        if not self.new_name:
            raise ValueError("Layer name cannot be empty.")
        self.label = f"Rename Layer: {self.new_name}"

    def execute(self):
        return self.tilemap.rename_layer(self.layer, self.new_name)

    def undo(self):
        return self.tilemap.rename_layer(self.layer, self.old_name)


class TileMapLayerPropertyCommand:
    """Undoable assignment of a layer property."""

    def __init__(self, layer, property_name: str, value) -> None:
        self.layer = layer
        self.property_name = str(property_name)
        self.value = value
        self.previous = getattr(layer, self.property_name)
        self.label = f"Set Layer {self.property_name}"

    def execute(self):
        if self.property_name == "role":
            self.value = normalize_layer_role(self.value)
        setattr(self.layer, self.property_name, self.value)
        return self.layer

    def undo(self):
        setattr(self.layer, self.property_name, self.previous)
        return self.layer
