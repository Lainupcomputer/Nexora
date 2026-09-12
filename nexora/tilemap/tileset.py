from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class TileRegion:
    """
    Describes one tile inside a TileSet.

    index:
        Linear tile index in row-major order.

    column / row:
        Grid position inside the sprite sheet.

    uv:
        Nexora sprite UV format:

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
    Describes a regular tile sheet.

    TileSet itself does not own or load a texture.
    It only describes the tile grid and calculates regions/UVs.

    Example:

        tileset = TileSet(
            columns=16,
            rows=16,
            tile_width=32,
            tile_height=32,
        )

        grass = tileset.region(
            5
        )

        renderer.sprite(
            texture,
            x,
            y,
            width=32,
            height=32,
            uv=grass.uv,
        )
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
        """
        Total number of available tiles.
        """

        return (
            self.columns
            * self.rows
        )

    @property
    def texture_width(
        self,
    ) -> int:
        """
        Expected sprite-sheet width in pixels.
        """

        return (
            self.columns
            * self.tile_width
        )

    @property
    def texture_height(
        self,
    ) -> int:
        """
        Expected sprite-sheet height in pixels.
        """

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

    # ==============================================================
    # Validation
    # ==============================================================

    def contains(
        self,
        index: int,
    ) -> bool:
        """
        Return True if a tile index exists.
        """

        return (
            0
            <= index
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
                f"TileSet range "
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
                f"TileSet range "
                f"0..{self.columns - 1}."
            )

        if (
            row < 0
            or row >= self.rows
        ):
            raise IndexError(
                f"Tile row {row} is outside "
                f"TileSet range "
                f"0..{self.rows - 1}."
            )

        return (
            column,
            row,
        )

    # ==============================================================
    # Index / grid conversion
    # ==============================================================

    def index(
        self,
        column: int,
        row: int,
    ) -> int:
        """
        Convert grid coordinates to a linear tile index.
        """

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
        """
        Convert a linear tile index to:

            (
                column,
                row,
            )
        """

        index = (
            self._validate_index(
                index
            )
        )

        column = (
            index
            % self.columns
        )

        row = (
            index
            // self.columns
        )

        return (
            column,
            row,
        )

    # ==============================================================
    # UV
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
        Return Nexora UV coordinates for a tile.

        Format:

            (
                uv_x,
                uv_y,
                uv_width,
                uv_height,
            )
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
        """
        Return UV coordinates directly from grid coordinates.
        """

        return self.uv(
            self.index(
                column,
                row,
            )
        )

    # ==============================================================
    # Region
    # ==============================================================

    def region(
        self,
        index: int,
    ) -> TileRegion:
        """
        Return complete information about one tile.
        """

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
        """
        Return a region using tile grid coordinates.
        """

        return self.region(
            self.index(
                column,
                row,
            )
        )

    # ==============================================================
    # Pixel regions
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
        Return the tile rectangle inside the source texture:

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