from __future__ import annotations

from dataclasses import dataclass
from nexora.tilemap.tile_metadata import TileMetadata
from nexora.tilemap.animation import TileAnimation


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
        texture_asset: str | None = None,
        spacing_x: int = 0,
        spacing_y: int = 0,
        margin_x: int = 0,
        margin_y: int = 0,
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

        spacing_x = int(spacing_x)
        spacing_y = int(spacing_y)
        margin_x = int(margin_x)
        margin_y = int(margin_y)
        if spacing_x < 0 or spacing_y < 0:
            raise ValueError("TileSet spacing cannot be negative.")
        if margin_x < 0 or margin_y < 0:
            raise ValueError("TileSet margins cannot be negative.")

        self.name = name

        self.columns = columns
        self.rows = rows

        self.tile_width = tile_width
        self.tile_height = tile_height
        self.texture_asset = None if texture_asset is None else str(texture_asset)
        self.spacing_x = spacing_x
        self.spacing_y = spacing_y
        self.margin_x = margin_x
        self.margin_y = margin_y

        self._metadata: dict[
            int,
            TileMetadata,
        ] = {}

        self._animations: dict[int, TileAnimation] = {}

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
        return self.margin_x * 2 + self.columns * self.tile_width + max(0, self.columns - 1) * self.spacing_x

    @property
    def texture_height(
        self,
    ) -> int:
        return self.margin_y * 2 + self.rows * self.tile_height + max(0, self.rows - 1) * self.spacing_y

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

        texture_width = float(self.texture_width)
        texture_height = float(self.texture_height)
        uv_width = self.tile_width / texture_width
        uv_height = self.tile_height / texture_height
        pixel_x = self.margin_x + column * (self.tile_width + self.spacing_x)
        pixel_y = self.margin_y + row * (self.tile_height + self.spacing_y)

        return (
            pixel_x / texture_width,
            pixel_y / texture_height,

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
            self.margin_x + column * (self.tile_width + self.spacing_x),
            self.margin_y + row * (self.tile_height + self.spacing_y),

            self.tile_width,

            self.tile_height,
        )

    # ==============================================================
    # Metadata
    # ==============================================================

    def set_metadata(
        self,
        index: int,
        metadata: TileMetadata,
    ) -> None:
        index = self._validate_index(
            index
        )

        if not isinstance(
            metadata,
            TileMetadata,
        ):
            raise TypeError(
                "metadata must be TileMetadata."
            )

        self._metadata[
            index
        ] = metadata


    def get_metadata(
        self,
        index: int,
    ) -> TileMetadata | None:
        index = self._validate_index(
            index
        )

        return self._metadata.get(
            index
        )


    def require_metadata(
        self,
        index: int,
    ) -> TileMetadata:
        metadata = self.get_metadata(
            index
        )

        if metadata is None:
            raise KeyError(
                f"Tile {index} has no metadata."
            )

        return metadata


    def metadata(
        self,
        index: int,
    ) -> TileMetadata:
        """
        Return metadata for a tile.

        Creates default metadata when none exists yet.
        """

        index = self._validate_index(
            index
        )

        result = self._metadata.get(
            index
        )

        if result is None:
            result = TileMetadata()

            self._metadata[
                index
            ] = result

        return result


    def remove_metadata(
        self,
        index: int,
    ) -> TileMetadata | None:
        index = self._validate_index(
            index
        )

        return self._metadata.pop(
            index,
            None,
        )


    def is_solid(
        self,
        index: int,
    ) -> bool:
        metadata = self.get_metadata(
            index
        )

        if metadata is None:
            return False

        return metadata.solid


    def has_tag(
        self,
        index: int,
        tag: str,
    ) -> bool:
        metadata = self.get_metadata(
            index
        )

        if metadata is None:
            return False

        return metadata.has_tag(
            tag
        )

    # ==============================================================
    # Tile animations
    # ==============================================================

    def set_animation(self, index: int, animation: TileAnimation) -> None:
        index = self._validate_index(index)
        if not isinstance(animation, TileAnimation):
            raise TypeError("animation must be a TileAnimation")
        for frame in animation.frames:
            self._validate_index(frame.tile_id)
        self._animations[index] = animation

    def remove_animation(self, index: int) -> TileAnimation | None:
        return self._animations.pop(self._validate_index(index), None)

    def get_animation(self, index: int) -> TileAnimation | None:
        return self._animations.get(self._validate_index(index))

    def resolve_tile(self, index: int, elapsed: float = 0.0) -> int:
        index = self._validate_index(index)
        animation = self._animations.get(index)
        if animation is None:
            return index
        return animation.tile_at(elapsed)

    # ==============================================================
    # Asset / serialization helpers
    # ==============================================================

    def load_texture(self, assets, *, force_reload: bool = False):
        if not self.texture_asset:
            raise RuntimeError("TileSet has no texture_asset configured")
        return assets.texture(self.texture_asset, force_reload=force_reload)

    def to_state(self) -> dict:
        metadata = {}
        for index, item in self._metadata.items():
            metadata[int(index)] = {
                "solid": bool(item.solid),
                "tags": sorted(item.tags),
                "properties": dict(item.properties),
            }
        return {
            "name": self.name,
            "columns": self.columns,
            "rows": self.rows,
            "tile_width": self.tile_width,
            "tile_height": self.tile_height,
            "spacing_x": self.spacing_x,
            "spacing_y": self.spacing_y,
            "margin_x": self.margin_x,
            "margin_y": self.margin_y,
            "texture_asset": self.texture_asset,
            "metadata": metadata,
            "animations": {
                int(index): animation.to_state()
                for index, animation in self._animations.items()
            },
        }

    @classmethod
    def from_state(cls, state: dict) -> "TileSet":
        tileset = cls(
            name=str(state.get("name", "")),
            columns=int(state["columns"]),
            rows=int(state["rows"]),
            tile_width=int(state["tile_width"]),
            tile_height=int(state["tile_height"]),
            texture_asset=state.get("texture_asset"),
            spacing_x=int(state.get("spacing_x", state.get("gap_x", 0))),
            spacing_y=int(state.get("spacing_y", state.get("gap_y", 0))),
            margin_x=int(state.get("margin_x", 0)),
            margin_y=int(state.get("margin_y", 0)),
        )
        for raw_index, raw_meta in dict(state.get("metadata", {})).items():
            index = int(raw_index)
            data = dict(raw_meta)
            tileset.set_metadata(
                index,
                TileMetadata(
                    solid=bool(data.get("solid", False)),
                    tags=set(data.get("tags", ())),
                    properties=dict(data.get("properties", {})),
                ),
            )
        for raw_index, raw_animation in dict(state.get("animations", {})).items():
            tileset.set_animation(
                int(raw_index),
                TileAnimation.from_state(raw_animation),
            )
        return tileset
