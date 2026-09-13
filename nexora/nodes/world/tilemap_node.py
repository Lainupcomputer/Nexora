from __future__ import annotations

import math

from nexora.nodes.node import Node
from nexora.tilemap import (
    TileChunkRenderCache,
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

    Rendering uses:

        - viewport culling
        - chunk culling
        - empty-chunk skipping
        - chunk render caches
        - bulk GPU sprite submission
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
        # 1 means one extra row / column outside the viewport.
        self.culling_margin: int = 1

        # Rendering origin of the TileMap.
        #
        # When True:
        #
        #     local (0, 0)
        #
        # represents the center of the complete map.
        self.centered: bool = True

        # ======================================================
        # Chunk render cache
        # ======================================================

        self._chunk_caches: dict[
            tuple[
                int,
                int,
                int,
            ],
            TileChunkRenderCache,
        ] = {}

        # ======================================================
        # Debug / statistics
        # ======================================================

        self.last_visible_tiles: int = 0
        self.last_visible_chunks: int = 0
        self.last_rendered_tiles: int = 0

        self.last_cache_hits: int = 0
        self.last_cache_rebuilds: int = 0

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

        # A different map / tileset invalidates all previous
        # chunk render caches.
        self._chunk_caches.clear()

    # ==============================================================
    # Cache
    # ==============================================================

    def _get_chunk_cache(
        self,
        layer,
        chunk,
    ) -> TileChunkRenderCache:
        """
        Return the render cache for a specific layer/chunk pair.

        A cache is created lazily the first time the chunk becomes
        relevant for rendering.
        """

        key = (
            id(
                layer
            ),
            chunk.chunk_x,
            chunk.chunk_y,
        )

        cache = (
            self._chunk_caches.get(
                key
            )
        )

        if cache is None:
            cache = TileChunkRenderCache(
                chunk
            )

            self._chunk_caches[
                key
            ] = cache

        return cache

    def clear_chunk_caches(
        self,
    ) -> None:
        """
        Remove every cached chunk representation.

        The caches will be rebuilt lazily when needed.
        """

        self._chunk_caches.clear()

    @property
    def chunk_cache_count(
        self,
    ) -> int:
        return len(
            self._chunk_caches
        )

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
        Transform one tile center from local TileMap space into
        world coordinates.
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
    # Tile culling
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

        transform = (
            self.world_transform
        )

        # ------------------------------------------------------
        # Rotated maps
        # ------------------------------------------------------
        #
        # Proper rotated viewport projection will be implemented
        # separately.
        #
        # Until then, use the complete map as a conservative
        # fallback.
        # ------------------------------------------------------

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

        # Nexora world coordinates use the center of the viewport
        # as origin.

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
        # Map top-left position in world space
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

        min_x = (
            math.floor(
                (
                    viewport_left
                    - map_left
                )
                / tile_width
            )
            - margin
        )

        min_y = (
            math.floor(
                (
                    viewport_top
                    - map_top
                )
                / tile_height
            )
            - margin
        )

        max_x = (
            math.floor(
                (
                    viewport_right
                    - map_left
                )
                / tile_width
            )
            + margin
        )

        max_y = (
            math.floor(
                (
                    viewport_bottom
                    - map_top
                )
                / tile_height
            )
            + margin
        )

        # ------------------------------------------------------
        # Clamp against map
        # ------------------------------------------------------

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
    # Chunk culling
    # ==============================================================

    def visible_chunk_bounds(
        self,
        renderer,
        layer,
    ) -> tuple[
        int,
        int,
        int,
        int,
    ]:
        """
        Calculate visible chunk bounds for a TileLayer.

        Returns:

            (
                min_chunk_x,
                min_chunk_y,
                max_chunk_x,
                max_chunk_y,
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

        (
            min_tile_x,
            min_tile_y,
            max_tile_x,
            max_tile_y,
        ) = self.visible_bounds(
            renderer
        )

        if (
            max_tile_x < min_tile_x
            or max_tile_y < min_tile_y
        ):
            return (
                0,
                0,
                -1,
                -1,
            )

        chunk_size = (
            layer.chunk_size
        )

        min_chunk_x = (
            min_tile_x
            // chunk_size
        )

        min_chunk_y = (
            min_tile_y
            // chunk_size
        )

        max_chunk_x = (
            max_tile_x
            // chunk_size
        )

        max_chunk_y = (
            max_tile_y
            // chunk_size
        )

        # ------------------------------------------------------
        # Clamp against chunk grid
        # ------------------------------------------------------

        min_chunk_x = max(
            0,
            min_chunk_x,
        )

        min_chunk_y = max(
            0,
            min_chunk_y,
        )

        max_chunk_x = min(
            layer.chunk_columns - 1,
            max_chunk_x,
        )

        max_chunk_y = min(
            layer.chunk_rows - 1,
            max_chunk_y,
        )

        if (
            min_chunk_x > max_chunk_x
            or min_chunk_y > max_chunk_y
        ):
            return (
                0,
                0,
                -1,
                -1,
            )

        return (
            min_chunk_x,
            min_chunk_y,
            max_chunk_x,
            max_chunk_y,
        )

    # ==============================================================
    # Render
    # ==============================================================

    def render(
        self,
        renderer,
        interpolation: float,
    ) -> None:
        # ------------------------------------------------------
        # Statistics
        # ------------------------------------------------------

        self.last_visible_chunks = 0
        self.last_visible_tiles = 0
        self.last_rendered_tiles = 0

        self.last_cache_hits = 0
        self.last_cache_rebuilds = 0

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
        # Render dimensions
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
        # Exact visible tile bounds
        # ==========================================================

        (
            min_tile_x,
            min_tile_y,
            max_tile_x,
            max_tile_y,
        ) = self.visible_bounds(
            renderer
        )

        if (
            max_tile_x < min_tile_x
            or max_tile_y < min_tile_y
        ):
            return

        self.last_visible_tiles = (
            (
                max_tile_x
                - min_tile_x
                + 1
            )
            *
            (
                max_tile_y
                - min_tile_y
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

            # ======================================================
            # Visible chunk range
            # ======================================================

            (
                min_chunk_x,
                min_chunk_y,
                max_chunk_x,
                max_chunk_y,
            ) = self.visible_chunk_bounds(
                renderer,
                layer,
            )

            if (
                max_chunk_x < min_chunk_x
                or max_chunk_y < min_chunk_y
            ):
                continue

            sprites: list[
                tuple
            ] = []

            # ======================================================
            # Chunks
            # ======================================================

            for chunk_y in range(
                min_chunk_y,
                max_chunk_y + 1,
            ):
                for chunk_x in range(
                    min_chunk_x,
                    max_chunk_x + 1,
                ):
                    chunk = (
                        layer.get_chunk(
                            chunk_x,
                            chunk_y,
                        )
                    )

                    if chunk is None:
                        continue

                    self.last_visible_chunks += 1

                    # ==============================================
                    # Chunk cache
                    # ==============================================

                    cache = (
                        self._get_chunk_cache(
                            layer,
                            chunk,
                        )
                    )

                    was_valid = (
                        cache.valid
                    )

                    cached_tiles = (
                        cache.get(
                            self.tileset
                        )
                    )

                    if was_valid:
                        self.last_cache_hits += 1

                    else:
                        self.last_cache_rebuilds += 1

                    # Empty chunks are represented by an empty
                    # cache and require no more work.

                    if not cached_tiles:
                        continue

                    # ==============================================
                    # Chunk origin
                    # ==============================================

                    chunk_origin_x = (
                        chunk.chunk_x
                        * layer.chunk_size
                    )

                    chunk_origin_y = (
                        chunk.chunk_y
                        * layer.chunk_size
                    )

                    # ==============================================
                    # Cached tiles
                    # ==============================================

                    for cached_tile in cached_tiles:
                        x = (
                            chunk_origin_x
                            + cached_tile.x
                        )

                        y = (
                            chunk_origin_y
                            + cached_tile.y
                        )

                        # ------------------------------------------
                        # Exact tile culling
                        #
                        # The visible chunk may only partially be
                        # inside the viewport.
                        # ------------------------------------------

                        if (
                            x < min_tile_x
                            or x > max_tile_x
                            or y < min_tile_y
                            or y > max_tile_y
                        ):
                            continue

                        # ==========================================
                        # World position
                        # ==========================================

                        (
                            world_x,
                            world_y,
                        ) = self.tile_world_position(
                            x,
                            y,
                        )

                        # ==========================================
                        # GPU instance
                        # ==========================================

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
                                    cached_tile.uv_x
                                ),
                                float(
                                    cached_tile.uv_y
                                ),
                                float(
                                    cached_tile.uv_width
                                ),
                                float(
                                    cached_tile.uv_height
                                ),
                            )
                        )

            # ======================================================
            # Bulk GPU submission
            # ======================================================

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