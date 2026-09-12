from __future__ import annotations

import math
from dataclasses import dataclass

from nexora.tilemap.constants import EMPTY_TILE
from nexora.tilemap.tilemap import TileMap
from nexora.tilemap.tileset import TileSet


@dataclass(
    frozen=True,
    slots=True,
)
class SolidTileHit:
    """
    One solid tile overlapping a collision query.
    """

    layer_name: str

    tile_x: int
    tile_y: int

    tile_id: int

    world_x: float
    world_y: float

    width: float
    height: float

    @property
    def world_rect(
        self,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        """
        Rectangle format:

            (
                x,
                y,
                width,
                height,
            )

        x/y describe the top-left corner.
        """

        return (
            self.world_x,
            self.world_y,
            self.width,
            self.height,
        )

@dataclass(
    frozen=True,
    slots=True,
)
class TileMoveResult:
    """
    Result of an AABB movement against solid tiles.

    x / y:
        Final top-left world position.

    dx / dy:
        Movement that was actually applied.

    collided_*:
        Collision directions encountered while resolving movement.
    """

    x: float
    y: float

    dx: float
    dy: float

    collided_left: bool = False
    collided_right: bool = False
    collided_top: bool = False
    collided_bottom: bool = False

    @property
    def collided(
        self,
    ) -> bool:
        return (
            self.collided_left
            or self.collided_right
            or self.collided_top
            or self.collided_bottom
        )

    @property
    def position(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            self.x,
            self.y,
        )

    @property
    def movement(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            self.dx,
            self.dy,
        )


class TileCollision:
    """
    Collision/query helper for TileMap.

    This class does not move entities and does not resolve physics.

    It only provides efficient queries against tile metadata.
    """

    def __init__(
        self,
        tilemap: TileMap,
        tileset: TileSet,
    ) -> None:
        self.tilemap = tilemap
        self.tileset = tileset

        if (
            tilemap.tile_width
            != tileset.tile_width
            or tilemap.tile_height
            != tileset.tile_height
        ):
            raise ValueError(
                "TileMap tile size does not match TileSet tile size."
            )


    # ==============================================================
    # AABB movement
    # ==============================================================

    def move_aabb(
        self,
        layer_name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        dx: float,
        dy: float,
    ) -> TileMoveResult:
        """
        Move an axis-aligned rectangle against solid tiles.

        Collision is resolved separately:

            1. X axis
            2. Y axis

        This prevents diagonal movement from tunnelling through simple
        tile walls and makes collision response predictable.
        """

        x = float(
            x
        )

        y = float(
            y
        )

        width = float(
            width
        )

        height = float(
            height
        )

        dx = float(
            dx
        )

        dy = float(
            dy
        )

        if width <= 0.0:
            raise ValueError(
                "width must be greater than zero."
            )

        if height <= 0.0:
            raise ValueError(
                "height must be greater than zero."
            )

        start_x = x
        start_y = y

        collided_left = False
        collided_right = False
        collided_top = False
        collided_bottom = False

        # ==========================================================
        # X axis
        # ==========================================================

        if dx != 0.0:
            (
                x,
                collided_left,
                collided_right,
            ) = self._move_aabb_x(
                layer_name,
                x,
                y,
                width,
                height,
                dx,
            )

        # ==========================================================
        # Y axis
        # ==========================================================

        if dy != 0.0:
            (
                y,
                collided_top,
                collided_bottom,
            ) = self._move_aabb_y(
                layer_name,
                x,
                y,
                width,
                height,
                dy,
            )

        return TileMoveResult(
            x=x,
            y=y,
            dx=x - start_x,
            dy=y - start_y,
            collided_left=collided_left,
            collided_right=collided_right,
            collided_top=collided_top,
            collided_bottom=collided_bottom,
        )


    def _move_aabb_x(
        self,
        layer_name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        dx: float,
    ) -> tuple[
        float,
        bool,
        bool,
    ]:
        """
        Resolve horizontal AABB movement.

        Returns:

            (
                resolved_x,
                collided_left,
                collided_right,
            )
        """

        target_x = (
            x
            + dx
        )

        collided_left = False
        collided_right = False

        # ----------------------------------------------------------
        # Moving right
        # ----------------------------------------------------------

        if dx > 0.0:
            swept_x = x

            swept_width = (
                width
                + dx
            )

            hits = self.solid_tiles_in_rect(
                layer_name,
                swept_x,
                y,
                swept_width,
                height,
            )

            nearest_limit: float | None = None

            for hit in hits:
                tile_left = (
                    hit.world_x
                )

                # Tile must actually lie in front of the current
                # right edge.
                current_right = (
                    x
                    + width
                )

                if tile_left < current_right:
                    continue

                allowed_x = (
                    tile_left
                    - width
                )

                if (
                    nearest_limit is None
                    or allowed_x
                    < nearest_limit
                ):
                    nearest_limit = (
                        allowed_x
                    )

            if (
                nearest_limit is not None
                and target_x > nearest_limit
            ):
                target_x = (
                    nearest_limit
                )

                collided_right = True

        # ----------------------------------------------------------
        # Moving left
        # ----------------------------------------------------------

        else:
            swept_x = (
                x
                + dx
            )

            swept_width = (
                width
                - dx
            )

            hits = self.solid_tiles_in_rect(
                layer_name,
                swept_x,
                y,
                swept_width,
                height,
            )

            nearest_limit = None

            for hit in hits:
                tile_right = (
                    hit.world_x
                    + hit.width
                )

                # Tile must actually lie left of the current AABB.
                if tile_right > x:
                    continue

                allowed_x = (
                    tile_right
                )

                if (
                    nearest_limit is None
                    or allowed_x
                    > nearest_limit
                ):
                    nearest_limit = (
                        allowed_x
                    )

            if (
                nearest_limit is not None
                and target_x < nearest_limit
            ):
                target_x = (
                    nearest_limit
                )

                collided_left = True

        return (
            target_x,
            collided_left,
            collided_right,
        )


    def _move_aabb_y(
        self,
        layer_name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        dy: float,
    ) -> tuple[
        float,
        bool,
        bool,
    ]:
        """
        Resolve vertical AABB movement.

        Returns:

            (
                resolved_y,
                collided_top,
                collided_bottom,
            )
        """

        target_y = (
            y
            + dy
        )

        collided_top = False
        collided_bottom = False

        # ----------------------------------------------------------
        # Moving down
        # ----------------------------------------------------------

        if dy > 0.0:
            swept_y = y

            swept_height = (
                height
                + dy
            )

            hits = self.solid_tiles_in_rect(
                layer_name,
                x,
                swept_y,
                width,
                swept_height,
            )

            nearest_limit: float | None = None

            for hit in hits:
                tile_top = (
                    hit.world_y
                )

                current_bottom = (
                    y
                    + height
                )

                if tile_top < current_bottom:
                    continue

                allowed_y = (
                    tile_top
                    - height
                )

                if (
                    nearest_limit is None
                    or allowed_y
                    < nearest_limit
                ):
                    nearest_limit = (
                        allowed_y
                    )

            if (
                nearest_limit is not None
                and target_y > nearest_limit
            ):
                target_y = (
                    nearest_limit
                )

                collided_bottom = True

        # ----------------------------------------------------------
        # Moving up
        # ----------------------------------------------------------

        else:
            swept_y = (
                y
                + dy
            )

            swept_height = (
                height
                - dy
            )

            hits = self.solid_tiles_in_rect(
                layer_name,
                x,
                swept_y,
                width,
                swept_height,
            )

            nearest_limit = None

            for hit in hits:
                tile_bottom = (
                    hit.world_y
                    + hit.height
                )

                if tile_bottom > y:
                    continue

                allowed_y = (
                    tile_bottom
                )

                if (
                    nearest_limit is None
                    or allowed_y
                    > nearest_limit
                ):
                    nearest_limit = (
                        allowed_y
                    )

            if (
                nearest_limit is not None
                and target_y < nearest_limit
            ):
                target_y = (
                    nearest_limit
                )

                collided_top = True

        return (
            target_y,
            collided_top,
            collided_bottom,
        )

    # ==============================================================
    # Tile queries
    # ==============================================================

    def tile_id(
        self,
        layer_name: str,
        x: int,
        y: int,
    ) -> int:
        """
        Return the tile ID at a map coordinate.
        """

        layer = self.tilemap.require_layer(
            layer_name
        )

        return layer.get_tile(
            x,
            y,
        )

    def is_solid(
        self,
        layer_name: str,
        x: int,
        y: int,
    ) -> bool:
        """
        Return True when the tile at x/y is solid.

        Empty cells are never solid.
        """

        tile_id = self.tile_id(
            layer_name,
            x,
            y,
        )

        if tile_id == EMPTY_TILE:
            return False

        if not self.tileset.contains(
            tile_id
        ):
            raise IndexError(
                f"Tile ID {tile_id} in "
                f"layer {layer_name!r} "
                f"is outside TileSet range."
            )

        return self.tileset.is_solid(
            tile_id
        )

    # ==============================================================
    # Coordinate conversion
    # ==============================================================

    def world_to_tile(
        self,
        x: float,
        y: float,
    ) -> tuple[
        int,
        int,
    ]:
        """
        Convert top-left-based world coordinates to tile coordinates.
        """

        return (
            math.floor(
                float(x)
                / self.tilemap.tile_width
            ),
            math.floor(
                float(y)
                / self.tilemap.tile_height
            ),
        )

    def tile_world_rect(
        self,
        x: int,
        y: int,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        """
        Return the world-space rectangle of a tile.

        Rectangle uses top-left coordinates.
        """

        if not self.tilemap.contains(
            x,
            y,
        ):
            raise IndexError(
                f"Tile coordinate ({x}, {y}) is outside "
                f"TileMap size "
                f"{self.tilemap.width}x{self.tilemap.height}."
            )

        return (
            float(
                x
                * self.tilemap.tile_width
            ),
            float(
                y
                * self.tilemap.tile_height
            ),
            float(
                self.tilemap.tile_width
            ),
            float(
                self.tilemap.tile_height
            ),
        )

    # ==============================================================
    # Rectangle → tile range
    # ==============================================================

    def tile_bounds_for_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> tuple[
        int,
        int,
        int,
        int,
    ]:
        """
        Convert a world-space rectangle to an inclusive tile range.

        Returns:

            (
                min_x,
                min_y,
                max_x,
                max_y,
            )

        Result is clamped to the TileMap.

        When the rectangle does not overlap the map, returns:

            (
                0,
                0,
                -1,
                -1,
            )
        """

        x = float(
            x
        )

        y = float(
            y
        )

        width = float(
            width
        )

        height = float(
            height
        )

        if width <= 0.0:
            raise ValueError(
                "width must be greater than zero."
            )

        if height <= 0.0:
            raise ValueError(
                "height must be greater than zero."
            )

        rect_right = (
            x
            + width
        )

        rect_bottom = (
            y
            + height
        )

        map_right = float(
            self.tilemap.pixel_width
        )

        map_bottom = float(
            self.tilemap.pixel_height
        )

        # Rectangle completely outside map.

        if (
            rect_right <= 0.0
            or rect_bottom <= 0.0
            or x >= map_right
            or y >= map_bottom
        ):
            return (
                0,
                0,
                -1,
                -1,
            )

        tile_width = (
            self.tilemap.tile_width
        )

        tile_height = (
            self.tilemap.tile_height
        )

        min_x = math.floor(
            x
            / tile_width
        )

        min_y = math.floor(
            y
            / tile_height
        )

        # Subtract a tiny epsilon so a rectangle ending exactly on
        # a tile border does not include the next tile.

        epsilon = 1e-9

        max_x = math.floor(
            (
                rect_right
                - epsilon
            )
            / tile_width
        )

        max_y = math.floor(
            (
                rect_bottom
                - epsilon
            )
            / tile_height
        )

        min_x = max(
            0,
            min_x,
        )

        min_y = max(
            0,
            min_y,
        )

        max_x = min(
            self.tilemap.width - 1,
            max_x,
        )

        max_y = min(
            self.tilemap.height - 1,
            max_y,
        )

        if (
            min_x > max_x
            or min_y > max_y
        ):
            return (
                0,
                0,
                -1,
                -1,
            )

        return (
            min_x,
            min_y,
            max_x,
            max_y,
        )

    # ==============================================================
    # Solid tile queries
    # ==============================================================

    def solid_tiles_in_rect(
        self,
        layer_name: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> list[
        SolidTileHit
    ]:
        """
        Return every solid tile touched by a world-space rectangle.
        """

        layer = self.tilemap.require_layer(
            layer_name
        )

        (
            min_x,
            min_y,
            max_x,
            max_y,
        ) = self.tile_bounds_for_rect(
            x,
            y,
            width,
            height,
        )

        if (
            max_x < min_x
            or max_y < min_y
        ):
            return []

        hits: list[
            SolidTileHit
        ] = []

        for tile_y in range(
            min_y,
            max_y + 1,
        ):
            for tile_x in range(
                min_x,
                max_x + 1,
            ):
                tile_id = layer.get_tile(
                    tile_x,
                    tile_y,
                )

                if tile_id == EMPTY_TILE:
                    continue

                if not self.tileset.contains(
                    tile_id
                ):
                    raise IndexError(
                        f"Tile ID {tile_id} in "
                        f"layer {layer_name!r} "
                        f"is outside TileSet range."
                    )

                if not self.tileset.is_solid(
                    tile_id
                ):
                    continue

                world_x = float(
                    tile_x
                    * self.tilemap.tile_width
                )

                world_y = float(
                    tile_y
                    * self.tilemap.tile_height
                )

                hits.append(
                    SolidTileHit(
                        layer_name=layer_name,
                        tile_x=tile_x,
                        tile_y=tile_y,
                        tile_id=tile_id,
                        world_x=world_x,
                        world_y=world_y,
                        width=float(
                            self.tilemap.tile_width
                        ),
                        height=float(
                            self.tilemap.tile_height
                        ),
                    )
                )

        return hits

    def any_solid_in_rect(
        self,
        layer_name: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> bool:
        """
        Fast boolean version of solid_tiles_in_rect().
        """

        layer = self.tilemap.require_layer(
            layer_name
        )

        (
            min_x,
            min_y,
            max_x,
            max_y,
        ) = self.tile_bounds_for_rect(
            x,
            y,
            width,
            height,
        )

        if (
            max_x < min_x
            or max_y < min_y
        ):
            return False

        for tile_y in range(
            min_y,
            max_y + 1,
        ):
            for tile_x in range(
                min_x,
                max_x + 1,
            ):
                tile_id = layer.get_tile(
                    tile_x,
                    tile_y,
                )

                if tile_id == EMPTY_TILE:
                    continue

                if not self.tileset.contains(
                    tile_id
                ):
                    raise IndexError(
                        f"Tile ID {tile_id} in "
                        f"layer {layer_name!r} "
                        f"is outside TileSet range."
                    )

                if self.tileset.is_solid(
                    tile_id
                ):
                    return True

        return False