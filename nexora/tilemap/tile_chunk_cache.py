from __future__ import annotations

from dataclasses import dataclass

from nexora.tilemap.tile_chunk import TileChunk
from nexora.tilemap.tileset import TileSet


@dataclass(
    frozen=True,
    slots=True,
)
class CachedTile:
    """
    Precomputed static rendering information for one tile.

    Coordinates are local to the chunk.
    """

    x: int
    y: int

    tile_id: int

    uv_x: float
    uv_y: float
    uv_width: float
    uv_height: float

    @property
    def uv(
        self,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        return (
            self.uv_x,
            self.uv_y,
            self.uv_width,
            self.uv_height,
        )


class TileChunkRenderCache:
    """
    Cached rendering information for a TileChunk.

    The cache contains only information that does not depend on
    the TileMapNode transform:

        - local tile position
        - tile ID
        - UV coordinates

    World position, scale, rotation, opacity and flipping remain
    the responsibility of TileMapNode.
    """

    def __init__(
        self,
        chunk: TileChunk,
    ) -> None:
        self.chunk = chunk

        self._tiles: tuple[
            CachedTile,
            ...
        ] = ()

        self._valid = False

        self._build_count = 0

    # ==============================================================
    # Properties
    # ==============================================================

    @property
    def valid(
        self,
    ) -> bool:
        return (
            self._valid
            and not self.chunk.dirty
        )

    @property
    def tiles(
        self,
    ) -> tuple[
        CachedTile,
        ...
    ]:
        return self._tiles

    @property
    def tile_count(
        self,
    ) -> int:
        return len(
            self._tiles
        )

    @property
    def build_count(
        self,
    ) -> int:
        """
        Number of times this cache has actually been rebuilt.

        Useful for tests and later profiling.
        """

        return self._build_count

    # ==============================================================
    # Cache control
    # ==============================================================

    def invalidate(
        self,
    ) -> None:
        self._valid = False

    def clear(
        self,
    ) -> None:
        self._tiles = ()
        self._valid = False

    # ==============================================================
    # Build
    # ==============================================================

    def rebuild(
        self,
        tileset: TileSet,
    ) -> tuple[
        CachedTile,
        ...
    ]:
        """
        Rebuild cached data from the current TileChunk.
        """

        tiles: list[
            CachedTile
        ] = []

        for (
            local_x,
            local_y,
            tile_id,
        ) in self.chunk.iter_non_empty():
            if not tileset.contains(
                tile_id
            ):
                raise IndexError(
                    f"Tile ID {tile_id} in "
                    f"chunk {self.chunk.coordinates} "
                    f"is outside TileSet range."
                )

            (
                uv_x,
                uv_y,
                uv_width,
                uv_height,
            ) = tileset.uv(
                tile_id
            )

            tiles.append(
                CachedTile(
                    x=local_x,
                    y=local_y,
                    tile_id=tile_id,
                    uv_x=float(
                        uv_x
                    ),
                    uv_y=float(
                        uv_y
                    ),
                    uv_width=float(
                        uv_width
                    ),
                    uv_height=float(
                        uv_height
                    ),
                )
            )

        self._tiles = tuple(
            tiles
        )

        self._valid = True
        self._build_count += 1

        # The render representation now matches the chunk data.
        self.chunk.mark_clean()

        return self._tiles

    def get(
        self,
        tileset: TileSet,
    ) -> tuple[
        CachedTile,
        ...
    ]:
        """
        Return cached tiles.

        Rebuild automatically when the cache is invalid or the
        underlying chunk became dirty.
        """

        if not self.valid:
            return self.rebuild(
                tileset
            )

        return self._tiles

    # ==============================================================
    # Python helpers
    # ==============================================================

    def __len__(
        self,
    ) -> int:
        return len(
            self._tiles
        )

    def __iter__(
        self,
    ):
        return iter(
            self._tiles
        )

    def __repr__(
        self,
    ) -> str:
        return (
            f"TileChunkRenderCache("
            f"chunk={self.chunk.coordinates}, "
            f"tiles={len(self._tiles)}, "
            f"valid={self.valid}, "
            f"build_count={self._build_count}"
            f")"
        )