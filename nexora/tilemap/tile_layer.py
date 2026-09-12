from __future__ import annotations

from collections.abc import Iterator


EMPTY_TILE = -1


class TileLayer:
    """
    Stores one 2D layer of tile IDs.

    TileLayer contains no rendering logic and no TileSet reference.

    Empty cells use:

        EMPTY_TILE = -1

    so tile ID 0 remains a valid tile.
    """

    def __init__(
        self,
        name: str,
        *,
        width: int,
        height: int,
        visible: bool = True,
        enabled: bool = True,
        opacity: float = 1.0,
    ) -> None:
        width = int(
            width
        )

        height = int(
            height
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

        self.name = name

        self.width = width
        self.height = height

        self.visible = bool(
            visible
        )

        self.enabled = bool(
            enabled
        )

        self.opacity = self._clamp_opacity(
            opacity
        )

        self._tiles: list[int] = [
            EMPTY_TILE
        ] * (
            width
            * height
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
        Immutable snapshot of the complete flat tile storage.
        """

        return tuple(
            self._tiles
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
            0
            <= int(x)
            < self.width
            and
            0
            <= int(y)
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

    def _index(
        self,
        x: int,
        y: int,
    ) -> int:
        x, y = (
            self._validate_cell(
                x,
                y,
            )
        )

        return (
            y
            * self.width
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
        """
        Return the tile ID at a cell.

        EMPTY_TILE means the cell is empty.
        """

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
    ) -> None:
        """
        Set one tile ID.

        Valid tile IDs are >= 0.

        Use clear_tile() for empty cells.
        """

        tile_id = int(
            tile_id
        )

        if tile_id < 0:
            raise ValueError(
                "tile_id must be >= 0. "
                "Use clear_tile() for empty cells."
            )

        index = (
            self._index(
                x,
                y,
            )
        )

        self._tiles[
            index
        ] = tile_id

    def clear_tile(
        self,
        x: int,
        y: int,
    ) -> None:
        """
        Clear one tile cell.
        """

        self._tiles[
            self._index(
                x,
                y,
            )
        ] = EMPTY_TILE

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
        """
        Clear the complete layer.
        """

        self._tiles[:] = [
            EMPTY_TILE
        ] * self.cell_count

    def fill(
        self,
        tile_id: int,
    ) -> None:
        """
        Fill the complete layer with one tile ID.
        """

        tile_id = int(
            tile_id
        )

        if tile_id < 0:
            raise ValueError(
                "tile_id must be >= 0."
            )

        self._tiles[:] = [
            tile_id
        ] * self.cell_count

    def fill_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        tile_id: int,
    ) -> None:
        """
        Fill a rectangular tile region.

        The rectangle must be completely inside the layer.
        """

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

        tile_id = int(
            tile_id
        )

        if width <= 0:
            raise ValueError(
                "width must be greater than zero."
            )

        if height <= 0:
            raise ValueError(
                "height must be greater than zero."
            )

        if tile_id < 0:
            raise ValueError(
                "tile_id must be >= 0."
            )

        self._validate_rect(
            x,
            y,
            width,
            height,
        )

        for row in range(
            y,
            y + height,
        ):
            start = (
                row
                * self.width
                + x
            )

            end = (
                start
                + width
            )

            self._tiles[
                start:end
            ] = [
                tile_id
            ] * width

    def clear_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        """
        Clear a rectangular tile region.
        """

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

        self._validate_rect(
            x,
            y,
            width,
            height,
        )

        for row in range(
            y,
            y + height,
        ):
            start = (
                row
                * self.width
                + x
            )

            end = (
                start
                + width
            )

            self._tiles[
                start:end
            ] = [
                EMPTY_TILE
            ] * width

    def _validate_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
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

    # ==============================================================
    # Search / iteration
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
        Iterate tiles as:

            (
                x,
                y,
                tile_id,
            )

        By default empty cells are skipped.
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
                tile_id = (
                    self._tiles[
                        row_offset
                        + x
                    ]
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

    def count_tiles(
        self,
    ) -> int:
        """
        Return number of non-empty cells.
        """

        return sum(
            1
            for tile_id
            in self._tiles
            if tile_id
            != EMPTY_TILE
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
        """
        Find every cell containing a tile ID.
        """

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

        for (
            x,
            y,
            current_tile,
        ) in self.iter_tiles():
            if current_tile == tile_id:
                result.append(
                    (
                        x,
                        y,
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