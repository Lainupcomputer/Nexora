from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from nexora.tilemap import EMPTY_TILE, TileProjection


@dataclass(frozen=True, slots=True)
class TileMapCellEdit:
    """The before/after value of one edited tile cell."""

    x: int
    y: int
    before: int
    after: int


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
