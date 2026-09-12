from __future__ import annotations

import math
from collections.abc import Iterator

from nexora.tilemap.constants import EMPTY_TILE
from nexora.tilemap.tile_chunk import TileChunk


class TileLayer:
    """
    Stores one 2D layer of tile IDs.

    Internally the layer is divided into TileChunks.

    Public tile coordinates are always global layer coordinates.

    Example:

        layer.set_tile(
            40,
            12,
            5,
        )

    With a chunk size of 32 this accesses:

        chunk:
            (1, 0)

        local tile:
            (8, 12)

    Empty cells use:

        EMPTY_TILE = -1

    Tile ID 0 remains a valid tile.
    """

    DEFAULT_CHUNK_SIZE = (
        TileChunk.DEFAULT_SIZE
    )

    def __init__(
        self,
        name: str,
        *,
        width: int,
        height: int,
        visible: bool = True,
        enabled: bool = True,
        opacity: float = 1.0,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> None:
        width = int(
            width
        )

        height = int(
            height
        )

        chunk_size = int(
            chunk_size
        )

        if not name:
            raise ValueError(
                "TileLayer name cannot be empty."
            )

        if width <= 0:
            raise ValueError(
                "width must be greater than zero."
            )

        if height <= 0:
            raise ValueError(
                "height must be greater than zero."
            )

        if chunk_size <= 0:
            raise ValueError(
                "chunk_size must be greater than zero."
            )

        self.name = name

        self.width = width
        self.height = height

        self.chunk_size = (
            chunk_size
        )

        self.visible = bool(
            visible
        )

        self.enabled = bool(
            enabled
        )

        self.opacity = (
            self._clamp_opacity(
                opacity
            )
        )

        # ======================================================
        # Chunk grid
        # ======================================================

        self._chunk_columns = (
            math.ceil(
                self.width
                / self.chunk_size
            )
        )

        self._chunk_rows = (
            math.ceil(
                self.height
                / self.chunk_size
            )
        )

        self._chunks: dict[
            tuple[int, int],
            TileChunk,
        ] = {}

        self._create_chunks()

    # ==============================================================
    # Chunk creation
    # ==============================================================

    def _create_chunks(
        self,
    ) -> None:
        for chunk_y in range(
            self._chunk_rows
        ):
            for chunk_x in range(
                self._chunk_columns
            ):
                start_x = (
                    chunk_x
                    * self.chunk_size
                )

                start_y = (
                    chunk_y
                    * self.chunk_size
                )

                width = min(
                    self.chunk_size,
                    self.width
                    - start_x,
                )

                height = min(
                    self.chunk_size,
                    self.height
                    - start_y,
                )

                self._chunks[
                    (
                        chunk_x,
                        chunk_y,
                    )
                ] = TileChunk(
                    chunk_x,
                    chunk_y,
                    width=width,
                    height=height,
                )

    # ==============================================================
    # Basic information
    # ==============================================================

    @property
    def size(
        self,
    ) -> tuple[
        int,
        int,
    ]:
        return (
            self.width,
            self.height,
        )

    @property
    def cell_count(
        self,
    ) -> int:
        return (
            self.width
            * self.height
        )

    @property
    def tiles(
        self,
    ) -> tuple[
        int,
        ...,
    ]:
        """
        Immutable flat row-major snapshot of all tiles.

        This preserves the old TileLayer API even though storage is
        now chunk based.
        """

        return tuple(
            tile_id
            for (
                _,
                _,
                tile_id,
            )
            in self.iter_tiles(
                include_empty=True
            )
        )

    # ==============================================================
    # Chunk information
    # ==============================================================

    @property
    def chunk_columns(
        self,
    ) -> int:
        return (
            self._chunk_columns
        )

    @property
    def chunk_rows(
        self,
    ) -> int:
        return (
            self._chunk_rows
        )

    @property
    def chunk_count(
        self,
    ) -> int:
        return len(
            self._chunks
        )

    @property
    def chunk_grid_size(
        self,
    ) -> tuple[
        int,
        int,
    ]:
        return (
            self._chunk_columns,
            self._chunk_rows,
        )

    # ==============================================================
    # Validation
    # ==============================================================

    def contains(
        self,
        x: int,
        y: int,
    ) -> bool:
        x = int(
            x
        )

        y = int(
            y
        )

        return (
            0
            <= x
            < self.width
            and
            0
            <= y
            < self.height
        )

    def _validate_cell(
        self,
        x: int,
        y: int,
    ) -> tuple[
        int,
        int,
    ]:
        x = int(
            x
        )

        y = int(
            y
        )

        if not self.contains(
            x,
            y,
        ):
            raise IndexError(
                f"Tile coordinate "
                f"({x}, {y}) is outside "
                f"layer {self.name!r} "
                f"with size "
                f"{self.width}x{self.height}."
            )

        return (
            x,
            y,
        )

    # ==============================================================
    # Chunk coordinates
    # ==============================================================

    def chunk_coordinates(
        self,
        x: int,
        y: int,
    ) -> tuple[
        int,
        int,
    ]:
        """
        Convert global tile coordinates to chunk coordinates.
        """

        x, y = (
            self._validate_cell(
                x,
                y,
            )
        )

        return (
            x // self.chunk_size,
            y // self.chunk_size,
        )

    def local_coordinates(
        self,
        x: int,
        y: int,
    ) -> tuple[
        int,
        int,
    ]:
        """
        Convert global tile coordinates to local coordinates
        inside their chunk.
        """

        x, y = (
            self._validate_cell(
                x,
                y,
            )
        )

        return (
            x % self.chunk_size,
            y % self.chunk_size,
        )

    def resolve_tile(
        self,
        x: int,
        y: int,
    ) -> tuple[
        TileChunk,
        int,
        int,
    ]:
        """
        Resolve global tile coordinates into:

            (
                chunk,
                local_x,
                local_y,
            )
        """

        x, y = (
            self._validate_cell(
                x,
                y,
            )
        )

        chunk_x = (
            x
            // self.chunk_size
        )

        chunk_y = (
            y
            // self.chunk_size
        )

        local_x = (
            x
            - chunk_x
            * self.chunk_size
        )

        local_y = (
            y
            - chunk_y
            * self.chunk_size
        )

        chunk = (
            self._chunks[
                (
                    chunk_x,
                    chunk_y,
                )
            ]
        )

        return (
            chunk,
            local_x,
            local_y,
        )

    # ==============================================================
    # Chunk access
    # ==============================================================

    def get_chunk(
        self,
        chunk_x: int,
        chunk_y: int,
    ) -> TileChunk | None:
        """
        Return a chunk or None when chunk coordinates are outside
        the layer.
        """

        return self._chunks.get(
            (
                int(
                    chunk_x
                ),
                int(
                    chunk_y
                ),
            )
        )

    def require_chunk(
        self,
        chunk_x: int,
        chunk_y: int,
    ) -> TileChunk:
        chunk = self.get_chunk(
            chunk_x,
            chunk_y,
        )

        if chunk is None:
            raise IndexError(
                f"Chunk ({chunk_x}, {chunk_y}) "
                f"is outside layer "
                f"{self.name!r}."
            )

        return chunk

    def iter_chunks(
        self,
        *,
        include_empty: bool = True,
    ) -> Iterator[
        TileChunk
    ]:
        """
        Iterate chunks in row-major order.
        """

        for chunk_y in range(
            self._chunk_rows
        ):
            for chunk_x in range(
                self._chunk_columns
            ):
                chunk = (
                    self._chunks[
                        (
                            chunk_x,
                            chunk_y,
                        )
                    ]
                )

                if (
                    not include_empty
                    and chunk.empty
                ):
                    continue

                yield chunk

    def iter_dirty_chunks(
        self,
    ) -> Iterator[
        TileChunk
    ]:
        for chunk in self.iter_chunks():
            if chunk.dirty:
                yield chunk

    def mark_chunks_clean(
        self,
    ) -> None:
        for chunk in self.iter_chunks():
            chunk.mark_clean()

    def mark_chunks_dirty(
        self,
    ) -> None:
        for chunk in self.iter_chunks():
            chunk.mark_dirty()

    # ==============================================================
    # Tile access
    # ==============================================================

    def get_tile(
        self,
        x: int,
        y: int,
    ) -> int:
        chunk, local_x, local_y = (
            self.resolve_tile(
                x,
                y,
            )
        )

        return chunk.get_tile(
            local_x,
            local_y,
        )

    def set_tile(
        self,
        x: int,
        y: int,
        tile_id: int,
    ) -> None:
        tile_id = int(
            tile_id
        )

        if tile_id < 0:
            raise ValueError(
                "tile_id must be >= 0. "
                "Use clear_tile() for empty cells."
            )

        chunk, local_x, local_y = (
            self.resolve_tile(
                x,
                y,
            )
        )

        chunk.set_tile(
            local_x,
            local_y,
            tile_id,
        )

    def clear_tile(
        self,
        x: int,
        y: int,
    ) -> None:
        chunk, local_x, local_y = (
            self.resolve_tile(
                x,
                y,
            )
        )

        chunk.clear_tile(
            local_x,
            local_y,
        )

    def is_empty(
        self,
        x: int,
        y: int,
    ) -> bool:
        return (
            self.get_tile(
                x,
                y,
            )
            == EMPTY_TILE
        )

    # ==============================================================
    # Bulk operations
    # ==============================================================

    def clear(
        self,
    ) -> None:
        for chunk in self.iter_chunks():
            chunk.clear()

    def fill(
        self,
        tile_id: int,
    ) -> None:
        tile_id = int(
            tile_id
        )

        if tile_id < 0:
            raise ValueError(
                "tile_id must be >= 0."
            )

        for chunk in self.iter_chunks():
            for y in range(
                chunk.height
            ):
                for x in range(
                    chunk.width
                ):
                    chunk.set_tile(
                        x,
                        y,
                        tile_id,
                    )

    # ==============================================================
    # Rectangles
    # ==============================================================

    def _validate_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> tuple[
        int,
        int,
        int,
        int,
    ]:
        x = int(
            x
        )

        y = int(
            y
        )

        width = int(
            width
        )

        height = int(
            height
        )

        if width <= 0:
            raise ValueError(
                "width must be greater than zero."
            )

        if height <= 0:
            raise ValueError(
                "height must be greater than zero."
            )

        if (
            x < 0
            or y < 0
            or x + width
            > self.width
            or y + height
            > self.height
        ):
            raise IndexError(
                f"Tile rectangle "
                f"({x}, {y}, {width}, {height}) "
                f"is outside layer "
                f"{self.name!r} "
                f"with size "
                f"{self.width}x{self.height}."
            )

        return (
            x,
            y,
            width,
            height,
        )

    def fill_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        tile_id: int,
    ) -> None:
        tile_id = int(
            tile_id
        )

        if tile_id < 0:
            raise ValueError(
                "tile_id must be >= 0."
            )

        (
            x,
            y,
            width,
            height,
        ) = self._validate_rect(
            x,
            y,
            width,
            height,
        )

        for tile_y in range(
            y,
            y + height,
        ):
            for tile_x in range(
                x,
                x + width,
            ):
                self.set_tile(
                    tile_x,
                    tile_y,
                    tile_id,
                )

    def clear_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        (
            x,
            y,
            width,
            height,
        ) = self._validate_rect(
            x,
            y,
            width,
            height,
        )

        for tile_y in range(
            y,
            y + height,
        ):
            for tile_x in range(
                x,
                x + width,
            ):
                self.clear_tile(
                    tile_x,
                    tile_y,
                )

    # ==============================================================
    # Iteration
    # ==============================================================

    def iter_tiles(
        self,
        *,
        include_empty: bool = False,
    ) -> Iterator[
        tuple[
            int,
            int,
            int,
        ]
    ]:
        """
        Iterate tiles in global row-major order.

        Returns:

            (
                x,
                y,
                tile_id,
            )

        Maintaining global row-major order is important because this
        preserves the original TileLayer behaviour.
        """

        for y in range(
            self.height
        ):
            for x in range(
                self.width
            ):
                tile_id = (
                    self.get_tile(
                        x,
                        y,
                    )
                )

                if (
                    not include_empty
                    and tile_id
                    == EMPTY_TILE
                ):
                    continue

                yield (
                    x,
                    y,
                    tile_id,
                )

    def iter_chunk_tiles(
        self,
        chunk: TileChunk,
        *,
        include_empty: bool = False,
    ) -> Iterator[
        tuple[
            int,
            int,
            int,
        ]
    ]:
        """
        Iterate one chunk using GLOBAL layer coordinates.

        This will later be used by TileMapNode.
        """

        origin_x = (
            chunk.chunk_x
            * self.chunk_size
        )

        origin_y = (
            chunk.chunk_y
            * self.chunk_size
        )

        iterator = (
            chunk.iter_tiles()
            if include_empty
            else chunk.iter_non_empty()
        )

        for (
            local_x,
            local_y,
            tile_id,
        ) in iterator:
            yield (
                origin_x
                + local_x,

                origin_y
                + local_y,

                tile_id,
            )

    # ==============================================================
    # Statistics / search
    # ==============================================================

    def count_tiles(
        self,
    ) -> int:
        return sum(
            chunk.non_empty_count
            for chunk
            in self.iter_chunks()
        )

    def find_tiles(
        self,
        tile_id: int,
    ) -> list[
        tuple[
            int,
            int,
        ]
    ]:
        tile_id = int(
            tile_id
        )

        if tile_id < 0:
            raise ValueError(
                "tile_id must be >= 0."
            )

        result: list[
            tuple[
                int,
                int,
            ]
        ] = []

        for chunk in self.iter_chunks(
            include_empty=False
        ):
            for (
                x,
                y,
                current_tile,
            ) in self.iter_chunk_tiles(
                chunk
            ):
                if current_tile == tile_id:
                    result.append(
                        (
                            x,
                            y,
                        )
                    )

        # Previous API returned global row-major order.
        result.sort(
            key=lambda position: (
                position[1],
                position[0],
            )
        )

        return result

    # ==============================================================
    # Opacity
    # ==============================================================

    @staticmethod
    def _clamp_opacity(
        value: float,
    ) -> float:
        return max(
            0.0,
            min(
                1.0,
                float(
                    value
                ),
            ),
        )

    def set_opacity(
        self,
        value: float,
    ) -> None:
        self.opacity = (
            self._clamp_opacity(
                value
            )
        )