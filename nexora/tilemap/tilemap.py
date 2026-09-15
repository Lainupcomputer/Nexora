from __future__ import annotations

import math
from collections.abc import Iterator

from nexora.tilemap.tile_layer import TileLayer
from nexora.tilemap.projection import TileProjection


class TileMap:
    """
    Collection of tile layers sharing the same map dimensions.

    TileMap contains no rendering logic and no TileSet reference.

    It manages:

        - map dimensions
        - tile dimensions
        - layer order
        - layer lookup
        - layer creation/removal/reordering
    """

    def __init__(
        self,
        *,
        width: int,
        height: int,
        tile_width: int,
        tile_height: int,
        name: str = "",
        projection: TileProjection | str = TileProjection.ORTHOGONAL,
    ) -> None:
        width = int(
            width
        )

        height = int(
            height
        )

        tile_width = int(
            tile_width
        )

        tile_height = int(
            tile_height
        )

        if width <= 0:
            raise ValueError(
                "width must be greater than zero."
            )

        if height <= 0:
            raise ValueError(
                "height must be greater than zero."
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

        self.width = width
        self.height = height

        self.tile_width = tile_width
        self.tile_height = tile_height
        self.projection = TileProjection.coerce(projection)

        self._layers: list[
            TileLayer
        ] = []

        self._layer_lookup: dict[
            str,
            TileLayer,
        ] = {}

    # ==============================================================
    # Dimensions
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
    def pixel_width(
        self,
    ) -> int:
        if self.projection is TileProjection.ISOMETRIC:
            return int((self.width + self.height) * self.tile_width / 2.0)
        return self.width * self.tile_width

    @property
    def pixel_height(
        self,
    ) -> int:
        if self.projection is TileProjection.ISOMETRIC:
            return int((self.width + self.height) * self.tile_height / 2.0)
        return self.height * self.tile_height

    @property
    def pixel_size(
        self,
    ) -> tuple[
        int,
        int,
    ]:
        return (
            self.pixel_width,
            self.pixel_height,
        )

    # ==============================================================
    # Layers
    # ==============================================================

    @property
    def layers(
        self,
    ) -> tuple[
        TileLayer,
        ...,
    ]:
        """
        Immutable snapshot of layers in render/order sequence.
        """

        return tuple(
            self._layers
        )

    @property
    def layer_names(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return tuple(
            layer.name
            for layer in self._layers
        )

    @property
    def layer_count(
        self,
    ) -> int:
        return len(
            self._layers
        )

    # ==============================================================
    # Create / add
    # ==============================================================

    def create_layer(
        self,
        name: str,
        *,
        visible: bool = True,
        enabled: bool = True,
        opacity: float = 1.0,
        index: int | None = None,
        render_layer: int = 0,
        y_sort: bool | None = None,
    ) -> TileLayer:
        """
        Create and add a layer matching the TileMap dimensions.
        """

        layer = TileLayer(
            name,
            width=self.width,
            height=self.height,
            visible=visible,
            enabled=enabled,
            opacity=opacity,
            render_layer=render_layer,
            y_sort=(self.projection is TileProjection.ISOMETRIC if y_sort is None else y_sort),
        )

        self.add_layer(
            layer,
            index=index,
        )

        return layer

    def add_layer(
        self,
        layer: TileLayer,
        *,
        index: int | None = None,
    ) -> None:
        """
        Add an existing TileLayer.

        The layer must match the TileMap dimensions and its name must
        be unique.
        """

        if not isinstance(
            layer,
            TileLayer,
        ):
            raise TypeError(
                "layer must be a TileLayer."
            )

        if not layer.name:
            raise ValueError(
                "TileLayer name cannot be empty."
            )

        if layer.name in self._layer_lookup:
            raise ValueError(
                f"Layer {layer.name!r} already exists."
            )

        if (
            layer.width != self.width
            or layer.height != self.height
        ):
            raise ValueError(
                f"Layer {layer.name!r} has size "
                f"{layer.width}x{layer.height}, "
                f"but TileMap requires "
                f"{self.width}x{self.height}."
            )

        if index is None:
            self._layers.append(
                layer
            )

        else:
            index = self._normalize_insert_index(
                index
            )

            self._layers.insert(
                index,
                layer,
            )

        self._layer_lookup[
            layer.name
        ] = layer

    # ==============================================================
    # Get / require
    # ==============================================================

    def get_layer(
        self,
        name: str,
    ) -> TileLayer | None:
        return self._layer_lookup.get(
            name
        )

    def require_layer(
        self,
        name: str,
    ) -> TileLayer:
        layer = self.get_layer(
            name
        )

        if layer is None:
            raise KeyError(
                f"Layer {name!r} does not exist."
            )

        return layer

    def has_layer(
        self,
        name: str,
    ) -> bool:
        return name in self._layer_lookup

    def layer_at(
        self,
        index: int,
    ) -> TileLayer:
        """
        Return layer by order index.

        Standard Python negative indexing is supported.
        """

        try:
            return self._layers[
                index
            ]

        except IndexError:
            raise IndexError(
                f"Layer index {index} is outside "
                f"TileMap layer range."
            ) from None

    def layer_index(
        self,
        name: str,
    ) -> int:
        """
        Return the order index of a named layer.
        """

        layer = self.require_layer(
            name
        )

        return self._layers.index(
            layer
        )

    # ==============================================================
    # Remove
    # ==============================================================

    def remove_layer(
        self,
        layer_or_name: TileLayer | str,
    ) -> TileLayer | None:
        """
        Remove a layer.

        Returns the removed layer, or None when a named layer does
        not exist.

        Passing a TileLayer that does not belong to this map also
        returns None.
        """

        if isinstance(
            layer_or_name,
            str,
        ):
            layer = self._layer_lookup.get(
                layer_or_name
            )

            if layer is None:
                return None

        elif isinstance(
            layer_or_name,
            TileLayer,
        ):
            layer = layer_or_name

            if (
                layer.name
                not in self._layer_lookup
                or self._layer_lookup[
                    layer.name
                ]
                is not layer
            ):
                return None

        else:
            raise TypeError(
                "layer_or_name must be a layer name "
                "or TileLayer."
            )

        self._layers.remove(
            layer
        )

        self._layer_lookup.pop(
            layer.name,
            None,
        )

        return layer

    def clear_layers(
        self,
    ) -> None:
        self._layers.clear()
        self._layer_lookup.clear()

    # ==============================================================
    # Reordering
    # ==============================================================

    def move_layer(
        self,
        layer_or_name: TileLayer | str,
        index: int,
    ) -> None:
        """
        Move an existing layer to another order index.

        Index is interpreted against the final layer order.
        """

        layer = self._resolve_layer(
            layer_or_name
        )

        target_index = (
            self._normalize_move_index(
                index
            )
        )

        current_index = (
            self._layers.index(
                layer
            )
        )

        if current_index == target_index:
            return

        self._layers.pop(
            current_index
        )

        self._layers.insert(
            target_index,
            layer,
        )

    def move_layer_up(
        self,
        layer_or_name: TileLayer | str,
    ) -> None:
        """
        Move layer one step toward the end of the layer list.
        """

        layer = self._resolve_layer(
            layer_or_name
        )

        index = self._layers.index(
            layer
        )

        if index >= len(
            self._layers
        ) - 1:
            return

        self.move_layer(
            layer,
            index + 1,
        )

    def move_layer_down(
        self,
        layer_or_name: TileLayer | str,
    ) -> None:
        """
        Move layer one step toward the beginning of the layer list.
        """

        layer = self._resolve_layer(
            layer_or_name
        )

        index = self._layers.index(
            layer
        )

        if index <= 0:
            return

        self.move_layer(
            layer,
            index - 1,
        )

    def move_layer_to_top(
        self,
        layer_or_name: TileLayer | str,
    ) -> None:
        self.move_layer(
            layer_or_name,
            len(
                self._layers
            ) - 1,
        )

    def move_layer_to_bottom(
        self,
        layer_or_name: TileLayer | str,
    ) -> None:
        self.move_layer(
            layer_or_name,
            0,
        )

    # ==============================================================
    # Coordinates
    # ==============================================================

    def contains(
        self,
        x: int,
        y: int,
    ) -> bool:
        """
        Return True when tile coordinates lie inside the map.
        """

        return (
            0
            <= int(x)
            < self.width
            and
            0
            <= int(y)
            < self.height
        )

    def tile_to_world(
        self,
        x: int,
        y: int,
    ) -> tuple[float, float]:
        """Convert tile coordinates to the tile center in local map space."""
        x = int(x)
        y = int(y)
        if not self.contains(x, y):
            raise IndexError(
                f"Tile coordinate ({x}, {y}) is outside "
                f"TileMap size {self.width}x{self.height}."
            )

        if self.projection is TileProjection.ISOMETRIC:
            half_w = self.tile_width / 2.0
            half_h = self.tile_height / 2.0
            # Offset X so the complete diamond starts at local x=0.
            origin_x = self.height * half_w
            return (
                origin_x + (x - y) * half_w,
                (x + y) * half_h + half_h,
            )

        return (
            x * self.tile_width + self.tile_width / 2.0,
            y * self.tile_height + self.tile_height / 2.0,
        )

    def world_to_tile(
        self,
        x: float,
        y: float,
    ) -> tuple[int, int]:
        """Convert local map coordinates to tile coordinates."""
        x = float(x)
        y = float(y)

        if self.projection is TileProjection.ISOMETRIC:
            half_w = self.tile_width / 2.0
            half_h = self.tile_height / 2.0
            origin_x = self.height * half_w
            dx = (x - origin_x) / half_w
            dy = (y - half_h) / half_h
            return (
                int(math.floor((dy + dx) / 2.0)),
                int(math.floor((dy - dx) / 2.0)),
            )

        return (
            int(x // self.tile_width),
            int(y // self.tile_height),
        )

    # ==============================================================
    # Serialization
    # ==============================================================

    def to_state(self) -> dict:
        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "tile_width": self.tile_width,
            "tile_height": self.tile_height,
            "projection": self.projection.value,
            "layers": [layer.to_state() for layer in self._layers],
        }

    @classmethod
    def from_state(cls, state: dict) -> "TileMap":
        tilemap = cls(
            name=str(state.get("name", "")),
            width=int(state["width"]),
            height=int(state["height"]),
            tile_width=int(state["tile_width"]),
            tile_height=int(state["tile_height"]),
            projection=state.get("projection", TileProjection.ORTHOGONAL.value),
        )
        for layer_state in state.get("layers", ()):
            tilemap.add_layer(TileLayer.from_state(dict(layer_state)))
        return tilemap

    # ==============================================================
    # Iteration
    # ==============================================================

    def __len__(
        self,
    ) -> int:
        return len(
            self._layers
        )

    def __contains__(
        self,
        name: object,
    ) -> bool:
        return name in self._layer_lookup

    def __iter__(
        self,
    ) -> Iterator[
        TileLayer
    ]:
        return iter(
            self._layers
        )

    # ==============================================================
    # Internal helpers
    # ==============================================================

    def _resolve_layer(
        self,
        layer_or_name: TileLayer | str,
    ) -> TileLayer:
        if isinstance(
            layer_or_name,
            str,
        ):
            return self.require_layer(
                layer_or_name
            )

        if isinstance(
            layer_or_name,
            TileLayer,
        ):
            existing = self._layer_lookup.get(
                layer_or_name.name
            )

            if existing is not layer_or_name:
                raise ValueError(
                    "TileLayer does not belong to this TileMap."
                )

            return layer_or_name

        raise TypeError(
            "layer_or_name must be a layer name "
            "or TileLayer."
        )

    def _normalize_insert_index(
        self,
        index: int,
    ) -> int:
        index = int(
            index
        )

        count = len(
            self._layers
        )

        if index < 0:
            index += (
                count
                + 1
            )

        if (
            index < 0
            or index > count
        ):
            raise IndexError(
                f"Layer insertion index {index} "
                f"is outside valid range "
                f"0..{count}."
            )

        return index

    def _normalize_move_index(
        self,
        index: int,
    ) -> int:
        index = int(
            index
        )

        count = len(
            self._layers
        )

        if count == 0:
            raise IndexError(
                "Cannot move a layer in an empty TileMap."
            )

        if index < 0:
            index += count

        if (
            index < 0
            or index >= count
        ):
            raise IndexError(
                f"Layer index {index} is outside "
                f"valid range 0..{count - 1}."
            )

        return index