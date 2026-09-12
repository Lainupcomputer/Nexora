from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class TileRegion:
    """
    Region of one tile inside a regular tile sheet.

    uv uses Nexora's sprite UV format:

        (
            uv_x,
            uv_y,
            uv_width,
            uv_height,
        )
    """

    index: int

    column: int
    row: int

    uv: tuple[
        float,
        float,
        float,
        float,
    ]


class TileSet:
    """
    Describes a regular grid-based tile sheet.

    TileSet does not own or load a texture.
    It only describes the source layout.
    """

    def __init__(
        self,
        *,
        columns: int,
        rows: int,
        tile_width: int,
        tile_height: int,
        name: str = "",
    ) -> None:
        columns = int(
            columns
        )

        rows = int(
            rows
        )

        tile_width = int(
            tile_width
        )

        tile_height = int(
            tile_height
        )

        if columns <= 0:
            raise ValueError(
                "columns must be greater than zero."
            )

        if rows <= 0:
            raise ValueError(
                "rows must be greater than zero."
            )

        if tile_width <= 0:
            raise ValueError(
                "tile_width must be greater than zero."
            )

        if tile_height <= 0:
            raise ValueError(
                "tile_height must be greater than zero."
            )

        self.name = name

        self.columns = columns
        self.rows = rows

        self.tile_width = tile_width
        self.tile_height = tile_height

    # ==============================================================
    # Dimensions
    # ==============================================================

    @property
    def tile_count(
        self,
    ) -> int:
        return (
            self.columns
            * self.rows
        )

    @property
    def tile_size(
        self,
    ) -> tuple[
        int,
        int,
    ]:
        return (
            self.tile_width,
            self.tile_height,
        )

    @property
    def texture_width(
        self,
    ) -> int:
        return (
            self.columns
            * self.tile_width
        )

    @property
    def texture_height(
        self,
    ) -> int:
        return (
            self.rows
            * self.tile_height
        )

    @property
    def texture_size(
        self,
    ) -> tuple[
        int,
        int,
    ]:
        return (
            self.texture_width,
            self.texture_height,
        )

    # ==============================================================
    # Validation
    # ==============================================================

    def contains(
        self,
        index: int,
    ) -> bool:
        return (
            0
            <= int(index)
            < self.tile_count
        )

    def _validate_index(
        self,
        index: int,
    ) -> int:
        index = int(
            index
        )

        if not self.contains(
            index
        ):
            raise IndexError(
                f"Tile index {index} is outside "
                f"the valid range "
                f"0..{self.tile_count - 1}."
            )

        return index

    def _validate_cell(
        self,
        column: int,
        row: int,
    ) -> tuple[
        int,
        int,
    ]:
        column = int(
            column
        )

        row = int(
            row
        )

        if (
            column < 0
            or column >= self.columns
        ):
            raise IndexError(
                f"Tile column {column} is outside "
                f"the valid range "
                f"0..{self.columns - 1}."
            )

        if (
            row < 0
            or row >= self.rows
        ):
            raise IndexError(
                f"Tile row {row} is outside "
                f"the valid range "
                f"0..{self.rows - 1}."
            )

        return (
            column,
            row,
        )

    # ==============================================================
    # Index / cell conversion
    # ==============================================================

    def index(
        self,
        column: int,
        row: int,
    ) -> int:
        column, row = (
            self._validate_cell(
                column,
                row,
            )
        )

        return (
            row
            * self.columns
            + column
        )

    def cell(
        self,
        index: int,
    ) -> tuple[
        int,
        int,
    ]:
        index = (
            self._validate_index(
                index
            )
        )

        return (
            index
            % self.columns,

            index
            // self.columns,
        )

    # ==============================================================
    # UVs
    # ==============================================================

    def uv(
        self,
        index: int,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        """
        Return Nexora sprite UV coordinates for a tile.
        """

        column, row = (
            self.cell(
                index
            )
        )

        uv_width = (
            1.0
            / float(
                self.columns
            )
        )

        uv_height = (
            1.0
            / float(
                self.rows
            )
        )

        return (
            column
            * uv_width,

            row
            * uv_height,

            uv_width,

            uv_height,
        )

    def uv_at(
        self,
        column: int,
        row: int,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        return self.uv(
            self.index(
                column,
                row,
            )
        )

    # ==============================================================
    # Regions
    # ==============================================================

    def region(
        self,
        index: int,
    ) -> TileRegion:
        index = (
            self._validate_index(
                index
            )
        )

        column, row = (
            self.cell(
                index
            )
        )

        return TileRegion(
            index=index,
            column=column,
            row=row,
            uv=self.uv(
                index
            ),
        )

    def region_at(
        self,
        column: int,
        row: int,
    ) -> TileRegion:
        return self.region(
            self.index(
                column,
                row,
            )
        )

    # ==============================================================
    # Pixel coordinates
    # ==============================================================

    def pixel_rect(
        self,
        index: int,
    ) -> tuple[
        int,
        int,
        int,
        int,
    ]:
        """
        Return the source pixel rectangle:

            (
                x,
                y,
                width,
                height,
            )
        """

        column, row = (
            self.cell(
                index
            )
        )

        return (
            column
            * self.tile_width,

            row
            * self.tile_height,

            self.tile_width,

            self.tile_height,
        )