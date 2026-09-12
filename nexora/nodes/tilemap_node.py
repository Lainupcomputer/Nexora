from __future__ import annotations

import math

from nexora.nodes.node import Node
from nexora.tilemap import (
    EMPTY_TILE,
    TileMap,
    TileSet,
)


class TileMapNode(Node):
    """
    Scene node for rendering a TileMap.

    TileMapNode references:

        - TileMap
        - TileSet
        - GPU texture

    but does not own any of them.

    Only visible tiles are submitted to the renderer.
    """

    def __init__(
        self,
        name: str,
        world,
    ) -> None:
        super().__init__(
            name,
            world,
        )

        # ======================================================
        # Resources
        # ======================================================

        self.tilemap: TileMap | None = None
        self.tileset: TileSet | None = None
        self.texture = None

        # ======================================================
        # Rendering
        # ======================================================

        self.culling_enabled: bool = True

        # Additional tile margin around the viewport.
        #
        # 1 means one extra row/column outside the viewport.
        self.culling_margin: int = 1

        # Rendering origin of the TileMap.
        #
        # By default local coordinate (0, 0) represents the center
        # of the complete map.
        self.centered: bool = True

        # Debug/statistics.
        self.last_visible_tiles: int = 0
        self.last_rendered_tiles: int = 0

    # ==============================================================
    # Configuration
    # ==============================================================

    def set_map(
        self,
        tilemap: TileMap,
        tileset: TileSet,
        texture,
    ) -> None:
        if (
            tilemap.tile_width
            != tileset.tile_width
            or tilemap.tile_height
            != tileset.tile_height
        ):
            raise ValueError(
                "TileMap tile size does not match TileSet tile size."
            )

        self.tilemap = tilemap
        self.tileset = tileset
        self.texture = texture

    # ==============================================================
    # Map information
    # ==============================================================

    @property
    def ready(
        self,
    ) -> bool:
        return (
            self.tilemap is not None
            and self.tileset is not None
            and self.texture is not None
        )

    @property
    def map_pixel_size(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        if self.tilemap is None:
            return (
                0.0,
                0.0,
            )

        return (
            float(
                self.tilemap.pixel_width
            ),
            float(
                self.tilemap.pixel_height
            ),
        )

    # ==============================================================
    # Local coordinates
    # ==============================================================

    def tile_local_position(
        self,
        x: int,
        y: int,
    ) -> tuple[
        float,
        float,
    ]:
        """
        Return the center of a tile in TileMapNode-local space.
        """

        if self.tilemap is None:
            raise RuntimeError(
                "TileMapNode has no TileMap."
            )

        if not self.tilemap.contains(
            x,
            y,
        ):
            raise IndexError(
                f"Tile ({x}, {y}) is outside the TileMap."
            )

        tile_width = (
            self.tilemap.tile_width
        )

        tile_height = (
            self.tilemap.tile_height
        )

        local_x = (
            x * tile_width
            + tile_width / 2.0
        )

        local_y = (
            y * tile_height
            + tile_height / 2.0
        )

        if self.centered:
            local_x -= (
                self.tilemap.pixel_width
                / 2.0
            )

            local_y -= (
                self.tilemap.pixel_height
                / 2.0
            )

        return (
            local_x,
            local_y,
        )

    # ==============================================================
    # World coordinates
    # ==============================================================

    def tile_world_position(
        self,
        x: int,
        y: int,
    ) -> tuple[
        float,
        float,
    ]:
        """
        Transform one tile center from local map space into world
        coordinates.
        """

        local_x, local_y = (
            self.tile_local_position(
                x,
                y,
            )
        )

        transform = (
            self.world_transform
        )

        scaled_x = (
            local_x
            * transform.scale_x
        )

        scaled_y = (
            local_y
            * transform.scale_y
        )

        if transform.rotation != 0.0:
            angle = math.radians(
                transform.rotation
            )

            cos_angle = math.cos(
                angle
            )

            sin_angle = math.sin(
                angle
            )

            rotated_x = (
                scaled_x
                * cos_angle
                - scaled_y
                * sin_angle
            )

            rotated_y = (
                scaled_x
                * sin_angle
                + scaled_y
                * cos_angle
            )

        else:
            rotated_x = scaled_x
            rotated_y = scaled_y

        return (
            transform.x
            + rotated_x,

            transform.y
            + rotated_y,
        )

    # ==============================================================
    # Culling
    # ==============================================================

    def visible_bounds(
        self,
        renderer,
    ) -> tuple[
        int,
        int,
        int,
        int,
    ]:
        """
        Calculate a conservative visible tile rectangle.

        Returns:

            (
                min_x,
                min_y,
                max_x,
                max_y,
            )

        max values are inclusive.
        """

        if self.tilemap is None:
            return (
                0,
                0,
                -1,
                -1,
            )

        # ------------------------------------------------------
        # Rotated TileMaps use a conservative full-map fallback.
        #
        # We can later replace this with proper rotated viewport
        # projection without changing the public API.
        # ------------------------------------------------------

        transform = (
            self.world_transform
        )

        if (
            not self.culling_enabled
            or transform.rotation != 0.0
        ):
            return (
                0,
                0,
                self.tilemap.width - 1,
                self.tilemap.height - 1,
            )

        scale_x = abs(
            transform.scale_x
        )

        scale_y = abs(
            transform.scale_y
        )

        if (
            scale_x <= 0.0
            or scale_y <= 0.0
        ):
            return (
                0,
                0,
                -1,
                -1,
            )

        tile_width = (
            self.tilemap.tile_width
            * scale_x
        )

        tile_height = (
            self.tilemap.tile_height
            * scale_y
        )

        # Nexora world/sprite coordinates use screen center as
        # viewport origin.
        viewport_left = (
            -renderer.width
            / 2.0
        )

        viewport_top = (
            -renderer.height
            / 2.0
        )

        viewport_right = (
            renderer.width
            / 2.0
        )

        viewport_bottom = (
            renderer.height
            / 2.0
        )

        # ------------------------------------------------------
        # Map top-left world position
        # ------------------------------------------------------

        if self.centered:
            map_left = (
                transform.x
                - (
                    self.tilemap.pixel_width
                    * scale_x
                )
                / 2.0
            )

            map_top = (
                transform.y
                - (
                    self.tilemap.pixel_height
                    * scale_y
                )
                / 2.0
            )

        else:
            map_left = (
                transform.x
            )

            map_top = (
                transform.y
            )

        margin = max(
            0,
            int(
                self.culling_margin
            ),
        )

        min_x = math.floor(
            (
                viewport_left
                - map_left
            )
            / tile_width
        ) - margin

        min_y = math.floor(
            (
                viewport_top
                - map_top
            )
            / tile_height
        ) - margin

        max_x = math.floor(
            (
                viewport_right
                - map_left
            )
            / tile_width
        ) + margin

        max_y = math.floor(
            (
                viewport_bottom
                - map_top
            )
            / tile_height
        ) + margin

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
    # Render
    # ==============================================================
    def render(
        self,
        renderer,
        interpolation: float,
    ) -> None:
        self.last_visible_tiles = 0
        self.last_rendered_tiles = 0

        if not self.ready:
            return

        assert self.tilemap is not None
        assert self.tileset is not None

        transform = (
            self.world_transform
        )

        scale_x = (
            transform.scale_x
        )

        scale_y = (
            transform.scale_y
        )

        if (
            scale_x == 0.0
            or scale_y == 0.0
        ):
            return

        # ==========================================================
        # Render size
        # ==========================================================

        tile_width = (
            self.tilemap.tile_width
            * abs(
                scale_x
            )
        )

        tile_height = (
            self.tilemap.tile_height
            * abs(
                scale_y
            )
        )

        flip_x = (
            scale_x < 0.0
        )

        flip_y = (
            scale_y < 0.0
        )

        # ==========================================================
        # Culling
        # ==========================================================

        (
            min_x,
            min_y,
            max_x,
            max_y,
        ) = self.visible_bounds(
            renderer
        )

        if (
            max_x < min_x
            or max_y < min_y
        ):
            return

        self.last_visible_tiles = (
            (
                max_x
                - min_x
                + 1
            )
            *
            (
                max_y
                - min_y
                + 1
            )
        )

        # ==========================================================
        # Layers
        # ==========================================================

        for layer in self.tilemap:
            if not layer.visible:
                continue

            if not layer.enabled:
                continue

            alpha = max(
                0.0,
                min(
                    1.0,
                    layer.opacity,
                ),
            )

            if alpha <= 0.0:
                continue

            # ------------------------------------------------------
            # Build one GPU batch for this layer
            # ------------------------------------------------------

            sprites: list[
                tuple[
                    float,
                    ...,
                ]
            ] = []

            for y in range(
                min_y,
                max_y + 1,
            ):
                for x in range(
                    min_x,
                    max_x + 1,
                ):
                    tile_id = (
                        layer.get_tile(
                            x,
                            y,
                        )
                    )

                    if tile_id == EMPTY_TILE:
                        continue

                    if not self.tileset.contains(
                        tile_id
                    ):
                        raise IndexError(
                            f"Tile ID {tile_id} in "
                            f"layer {layer.name!r} "
                            f"is outside TileSet range."
                        )

                    # ----------------------------------------------
                    # Position
                    # ----------------------------------------------

                    world_x, world_y = (
                        self.tile_world_position(
                            x,
                            y,
                        )
                    )

                    # ----------------------------------------------
                    # UV
                    # ----------------------------------------------

                    (
                        uv_x,
                        uv_y,
                        uv_width,
                        uv_height,
                    ) = self.tileset.uv(
                        tile_id
                    )

                    # ----------------------------------------------
                    # Instance
                    # ----------------------------------------------

                    sprites.append(
                        (
                            float(
                                world_x
                            ),
                            float(
                                world_y
                            ),

                            float(
                                tile_width
                            ),
                            float(
                                tile_height
                            ),

                            float(
                                transform.rotation
                            ),

                            0.5,
                            0.5,

                            float(
                                alpha
                            ),

                            bool(
                                flip_x
                            ),
                            bool(
                                flip_y
                            ),

                            float(
                                uv_x
                            ),
                            float(
                                uv_y
                            ),
                            float(
                                uv_width
                            ),
                            float(
                                uv_height
                            ),
                        )
                    )

            # ------------------------------------------------------
            # One bulk submission for this layer
            # ------------------------------------------------------

            if not sprites:
                continue

            rendered = (
                renderer.sprites(
                    self.texture,
                    sprites,
                )
            )

            self.last_rendered_tiles += (
                rendered
            )