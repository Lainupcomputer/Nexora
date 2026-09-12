from __future__ import annotations

from collections.abc import Iterator

from nexora.tilemap.constants import EMPTY_TILE


class TileChunk:
    """
    A rectangular block of tiles inside a TileLayer.

    TileChunk stores tile IDs in a compact flat list and tracks
    whether its contents have changed since the last rebuild.

    Chunk coordinates describe the position of the chunk inside
    the chunk grid, not tile coordinates.
    """

    DEFAULT_SIZE = 32

    def __init__(
        self,
        chunk_x: int,
        chunk_y: int,
        *,
        width: int = DEFAULT_SIZE,
        height: int = DEFAULT_SIZE,
    ) -> None:
        if chunk_x < 0:
            raise ValueError(
                "chunk_x must be >= 0."
            )

        if chunk_y < 0:
            raise ValueError(
                "chunk_y must be >= 0."
            )

        if width <= 0:
            raise ValueError(
                "width must be > 0."
            )

        if height <= 0:
            raise ValueError(
                "height must be > 0."
            )

        self.chunk_x = int(
            chunk_x
        )

        self.chunk_y = int(
            chunk_y
        )

        self.width = int(
            width
        )

        self.height = int(
            height
        )

        self._tiles: list[int] = [
            EMPTY_TILE
        ] * (
            self.width
            * self.height
        )

        # Newly created chunks have not yet been built for
        # rendering, therefore they start dirty.
        self._dirty = True

        self._non_empty_count = 0

    # ==============================================================
    # Properties
    # ==============================================================

    @property
    def dirty(
        self,
    ) -> bool:
        return self._dirty

    @property
    def empty(
        self,
    ) -> bool:
        return (
            self._non_empty_count
            == 0
        )

    @property
    def tile_count(
        self,
    ) -> int:
        return (
            self.width
            * self.height
        )

    @property
    def non_empty_count(
        self,
    ) -> int:
        return self._non_empty_count

    @property
    def coordinates(
        self,
    ) -> tuple[int, int]:
        return (
            self.chunk_x,
            self.chunk_y,
        )

    # ==============================================================
    # Validation
    # ==============================================================

    def contains(
        self,
        x: int,
        y: int,
    ) -> bool:
        return (
            0 <= x < self.width
            and
            0 <= y < self.height
        )

    def _index(
        self,
        x: int,
        y: int,
    ) -> int:
        if not self.contains(
            x,
            y,
        ):
            raise IndexError(
                f"Tile ({x}, {y}) is outside "
                f"chunk ({self.chunk_x}, {self.chunk_y}) "
                f"with size {self.width}x{self.height}."
            )

        return (
            y * self.width
            + x
        )

    # ==============================================================
    # Tile access
    # ==============================================================

    def get_tile(
        self,
        x: int,
        y: int,
    ) -> int:
        return self._tiles[
            self._index(
                x,
                y,
            )
        ]

    def set_tile(
        self,
        x: int,
        y: int,
        tile_id: int,
    ) -> bool:
        """
        Set a tile.

        Returns True when the tile actually changed.
        """

        index = self._index(
            x,
            y,
        )

        tile_id = int(
            tile_id
        )

        previous = (
            self._tiles[
                index
            ]
        )

        if previous == tile_id:
            return False

        if previous == EMPTY_TILE:
            if tile_id != EMPTY_TILE:
                self._non_empty_count += 1

        elif tile_id == EMPTY_TILE:
            self._non_empty_count -= 1

        self._tiles[
            index
        ] = tile_id

        self._dirty = True

        return True

    def clear_tile(
        self,
        x: int,
        y: int,
    ) -> bool:
        return self.set_tile(
            x,
            y,
            EMPTY_TILE,
        )

    # ==============================================================
    # Chunk operations
    # ==============================================================

    def clear(
        self,
    ) -> bool:
        """
        Clear all tiles.

        Returns True if the chunk changed.
        """

        if self.empty:
            return False

        self._tiles[:] = [
            EMPTY_TILE
        ] * self.tile_count

        self._non_empty_count = 0
        self._dirty = True

        return True

    def mark_dirty(
        self,
    ) -> None:
        self._dirty = True

    def mark_clean(
        self,
    ) -> None:
        self._dirty = False

    # ==============================================================
    # Iteration
    # ==============================================================

    def iter_tiles(
        self,
    ) -> Iterator[
        tuple[
            int,
            int,
            int,
        ]
    ]:
        """
        Iterate over every tile as:

            (local_x, local_y, tile_id)
        """

        for y in range(
            self.height
        ):
            row_offset = (
                y
                * self.width
            )

            for x in range(
                self.width
            ):
                yield (
                    x,
                    y,
                    self._tiles[
                        row_offset + x
                    ],
                )

    def iter_non_empty(
        self,
    ) -> Iterator[
        tuple[
            int,
            int,
            int,
        ]
    ]:
        """
        Iterate only over non-empty tiles.
        """

        for (
            x,
            y,
            tile_id,
        ) in self.iter_tiles():
            if tile_id == EMPTY_TILE:
                continue

            yield (
                x,
                y,
                tile_id,
            )

    # ==============================================================
    # Python helpers
    # ==============================================================

    def __len__(
        self,
    ) -> int:
        return self.tile_count

    def __repr__(
        self,
    ) -> str:
        return (
            f"TileChunk("
            f"chunk_x={self.chunk_x}, "
            f"chunk_y={self.chunk_y}, "
            f"width={self.width}, "
            f"height={self.height}, "
            f"non_empty={self._non_empty_count}, "
            f"dirty={self._dirty}"
            f")"
        )