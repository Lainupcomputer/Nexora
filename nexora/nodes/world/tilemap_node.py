from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

from nexora.nodes.node import Node
from nexora.tilemap import (
    TileChunkRenderCache,
    TileMap,
    TileSet,
    TileMetadataHit,
    TilePrefabSpawn,
    TileTeleportEvent,
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

        # Base render layer added to every TileLayer render_layer.
        self.base_render_layer: int = 0

        # Elapsed time used by animated tiles.
        self._animation_time: float = 0.0

        # Prefabs instantiated from TileMetadata.spawn.
        self._spawned_prefabs: list[TilePrefabSpawn] = []

        # Last tile visited by actors processed through the runtime trigger
        # helper. This provides enter-only semantics so a teleport tile cannot
        # fire once per frame while an actor is standing on it.
        self._tile_trigger_cells: dict[
            int,
            tuple[str, int, int] | None,
        ] = {}

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

    def set_map_from_assets(
        self,
        tilemap: TileMap,
        tileset: TileSet,
        assets,
        *,
        force_reload: bool = False,
    ) -> None:
        """Bind a TileMap using the TileSet texture_asset via AssetManager."""
        texture = tileset.load_texture(
            assets,
            force_reload=force_reload,
        )
        self.set_map(tilemap, tileset, texture)

    def update(self, delta_time: float) -> None:
        self._animation_time += max(0.0, float(delta_time))

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

        local_x, local_y = self.tilemap.tile_to_world(
            x,
            y,
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
    # Coordinate queries
    # ==============================================================

    def world_to_local_position(
        self,
        world_x: float,
        world_y: float,
    ) -> tuple[float, float]:
        """Convert a world-space position into TileMapNode-local space."""

        transform = self.world_transform

        x = float(world_x) - transform.x
        y = float(world_y) - transform.y

        if transform.rotation != 0.0:
            angle = math.radians(-transform.rotation)
            cos_angle = math.cos(angle)
            sin_angle = math.sin(angle)
            x, y = (
                x * cos_angle - y * sin_angle,
                x * sin_angle + y * cos_angle,
            )

        if transform.scale_x == 0.0 or transform.scale_y == 0.0:
            raise ValueError("TileMapNode world scale cannot be zero.")

        x /= transform.scale_x
        y /= transform.scale_y

        return (x, y)

    def world_to_tile(
        self,
        world_x: float,
        world_y: float,
    ) -> tuple[int, int]:
        """Convert a world-space point to integer tile coordinates."""

        if self.tilemap is None:
            raise RuntimeError("TileMapNode has no TileMap.")

        local_x, local_y = self.world_to_local_position(world_x, world_y)

        if self.centered:
            local_x += self.tilemap.pixel_width / 2.0
            local_y += self.tilemap.pixel_height / 2.0

        return self.tilemap.world_to_tile(local_x, local_y)

    # ==============================================================
    # Metadata queries
    # ==============================================================

    def metadata_at(
        self,
        layer_name: str,
        x: int,
        y: int,
    ) -> TileMetadataHit | None:
        """Return tile metadata for one map cell, or None when absent."""

        if self.tilemap is None or self.tileset is None:
            raise RuntimeError("TileMapNode has no TileMap/TileSet.")

        layer = self.tilemap.get_layer(layer_name)
        tile_id = layer.get_tile(
            int(x),
            int(y),
        )

        if (
            tile_id is None
            or int(tile_id) < 0
        ):
            return None

        metadata = self.tileset.get_metadata(tile_id)
        if metadata is None:
            return None

        return TileMetadataHit(
            layer_name=str(layer_name),
            tile_x=int(x),
            tile_y=int(y),
            tile_id=int(tile_id),
            metadata=metadata,
        )

    def metadata_at_world(
        self,
        layer_name: str,
        world_x: float,
        world_y: float,
    ) -> TileMetadataHit | None:
        """Resolve metadata for the tile under a world-space point."""

        x, y = self.world_to_tile(world_x, world_y)

        if self.tilemap is None or not self.tilemap.contains(x, y):
            return None

        return self.metadata_at(layer_name, x, y)

    def iter_metadata_tiles(
        self,
        *,
        layers: Iterable[str] | None = None,
        property_name: str | None = None,
        tag: str | None = None,
    ):
        """Yield tiles that have metadata, optionally filtered by property/tag."""

        if self.tilemap is None or self.tileset is None:
            raise RuntimeError("TileMapNode has no TileMap/TileSet.")

        wanted = None if layers is None else {str(name) for name in layers}

        for layer in self.tilemap.layers:
            if wanted is not None and layer.name not in wanted:
                continue

            for x, y, tile_id in layer.iter_tiles():
                if (
                    tile_id is None
                    or int(tile_id) < 0
                ):
                    continue

                metadata = self.tileset.get_metadata(tile_id)
                if metadata is None:
                    continue

                if property_name is not None and property_name not in metadata.properties:
                    continue

                if tag is not None and not metadata.has_tag(tag):
                    continue

                yield TileMetadataHit(
                    layer_name=layer.name,
                    tile_x=x,
                    tile_y=y,
                    tile_id=int(tile_id),
                    metadata=metadata,
                )

    # ==============================================================
    # Runtime tile triggers
    # ==============================================================

    def reset_tile_trigger(
        self,
        actor=None,
    ) -> None:
        """Reset enter-state for one actor or for all tracked actors."""

        if actor is None:
            self._tile_trigger_cells.clear()
            return

        self._tile_trigger_cells.pop(id(actor), None)

    def process_tile_triggers(
        self,
        actor,
        scene_manager,
        *,
        layer_name: str,
        loading_scene: str = "Loading",
        enter_transition=None,
        exit_transition=None,
        unload_previous: bool | None = None,
        context: dict | None = None,
        force_reload_assets: bool = False,
    ) -> TileTeleportEvent | None:
        """Process enter-only tile triggers for an actor.

        When the actor enters a tile whose TileMetadata.teleport property is
        set, the target is resolved through SceneManager and the existing
        begin_serialized_loading() pipeline is started.

        Teleport references may be either a registered serialized scene name
        or an .nxscene path/basename when SceneManager provides
        resolve_serialized_scene_name().
        """

        if self.tilemap is None or self.tileset is None:
            raise RuntimeError("TileMapNode has no TileMap/TileSet.")

        try:
            world_x, world_y = actor.world_position
        except Exception as exc:
            raise TypeError(
                "actor must expose a world_position (x, y) property."
            ) from exc

        tile_x, tile_y = self.world_to_tile(world_x, world_y)
        actor_key = id(actor)

        if not self.tilemap.contains(tile_x, tile_y):
            self._tile_trigger_cells[actor_key] = None
            return None

        cell = (str(layer_name), int(tile_x), int(tile_y))

        if self._tile_trigger_cells.get(actor_key) == cell:
            return None

        # Mark the cell before firing. If triggering fails we remove the mark so
        # the caller may retry after fixing registration/configuration.
        self._tile_trigger_cells[actor_key] = cell

        hit = self.metadata_at(layer_name, tile_x, tile_y)
        if hit is None:
            return None

        reference = hit.metadata.teleport
        if not reference:
            return None

        properties = hit.metadata.properties

        resolved_loading_scene = str(
            properties.get("teleport_loading_scene", loading_scene)
        )

        resolved_unload_previous = properties.get(
            "teleport_unload_previous",
            unload_previous,
        )
        if resolved_unload_previous is not None:
            resolved_unload_previous = bool(resolved_unload_previous)

        resolved_force_reload = bool(
            properties.get(
                "teleport_force_reload_assets",
                force_reload_assets,
            )
        )

        resolved_context = dict(context or {})
        metadata_context = properties.get("teleport_context")
        if metadata_context is not None:
            if not isinstance(metadata_context, dict):
                self._tile_trigger_cells.pop(actor_key, None)
                raise TypeError(
                    "teleport_context TileMetadata property must be a dict."
                )
            resolved_context.update(metadata_context)

        try:
            resolver = getattr(
                scene_manager,
                "resolve_serialized_scene_name",
                None,
            )
            scene_name = (
                resolver(reference)
                if callable(resolver)
                else str(reference)
            )

            scene_manager.begin_serialized_loading(
                scene_name,
                loading_scene=resolved_loading_scene,
                enter_transition=enter_transition,
                exit_transition=exit_transition,
                unload_previous=resolved_unload_previous,
                context=resolved_context,
                force_reload_assets=resolved_force_reload,
            )
        except Exception:
            self._tile_trigger_cells.pop(actor_key, None)
            raise

        return TileTeleportEvent(
            layer_name=hit.layer_name,
            tile_x=hit.tile_x,
            tile_y=hit.tile_y,
            tile_id=hit.tile_id,
            reference=str(reference),
            scene_name=str(scene_name),
            loading_scene=resolved_loading_scene,
            actor=actor,
        )

    # ==============================================================
    # Prefab spawning from TileMetadata.spawn
    # ==============================================================

    @property
    def spawned_prefabs(self) -> tuple[TilePrefabSpawn, ...]:
        return tuple(self._spawned_prefabs)

    def clear_spawned_prefabs(self) -> None:
        """Destroy every prefab previously spawned by this TileMapNode."""

        for item in reversed(self._spawned_prefabs):
            node = item.node
            try:
                node.destroy()
            except Exception:
                if node.parent is not None:
                    node.parent.remove_child(node)

        self._spawned_prefabs.clear()

    def spawn_prefabs(
        self,
        prefab_serializer,
        *,
        prefab_root: str | Path | None = None,
        context: dict | None = None,
        layers: Iterable[str] | None = None,
        clear_existing: bool = False,
    ) -> tuple[TilePrefabSpawn, ...]:
        """Instantiate prefabs declared through ``TileMetadata.spawn``.

        Spawned prefabs become children of the TileMapNode so their tile-local
        positions automatically inherit the map transform. ``spawn_overrides``
        in TileMetadata.properties may provide additional prefab root overrides.
        """

        if self.tilemap is None or self.tileset is None:
            raise RuntimeError("TileMapNode has no TileMap/TileSet.")

        if clear_existing:
            self.clear_spawned_prefabs()

        root = None if prefab_root is None else Path(prefab_root)
        spawned: list[TilePrefabSpawn] = []

        for hit in self.iter_metadata_tiles(layers=layers):
            source = hit.metadata.spawn
            if not source:
                continue

            path = Path(source)
            if root is not None and not path.is_absolute():
                path = root / path

            local_x, local_y = self.tile_local_position(hit.tile_x, hit.tile_y)

            overrides = dict(
                hit.metadata.get_property("spawn_overrides", {}) or {}
            )
            transform_overrides = dict(overrides.get("transform", {}) or {})
            transform_overrides["x"] = local_x
            transform_overrides["y"] = local_y
            overrides["transform"] = transform_overrides

            node = prefab_serializer.instantiate(
                path,
                self.world,
                parent=self,
                context=dict(context or {}),
                overrides=overrides,
            )

            result = TilePrefabSpawn(
                layer_name=hit.layer_name,
                tile_x=hit.tile_x,
                tile_y=hit.tile_y,
                tile_id=hit.tile_id,
                prefab_source=str(source),
                node=node,
            )

            self._spawned_prefabs.append(result)
            spawned.append(result)

        return tuple(spawned)

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
        # Isometric projection
        # ------------------------------------------------------

        if getattr(self.tilemap.projection, "value", self.tilemap.projection) == "isometric":
            if not self.culling_enabled or transform.rotation != 0.0:
                return (0, 0, self.tilemap.width - 1, self.tilemap.height - 1)

            scale_x = abs(transform.scale_x)
            scale_y = abs(transform.scale_y)
            if scale_x <= 0.0 or scale_y <= 0.0:
                return (0, 0, -1, -1)

            camera = getattr(renderer, "camera", None)
            camera_x = float(getattr(camera, "x", 0.0))
            camera_y = float(getattr(camera, "y", 0.0))
            half_vw = renderer.width / 2.0
            half_vh = renderer.height / 2.0

            # Convert viewport corners into map-local projected space,
            # then inverse-project them into tile coordinates.
            corners = []
            for world_x, world_y in (
                (camera_x - half_vw, camera_y - half_vh),
                (camera_x + half_vw, camera_y - half_vh),
                (camera_x - half_vw, camera_y + half_vh),
                (camera_x + half_vw, camera_y + half_vh),
            ):
                local_x = (world_x - transform.x) / transform.scale_x
                local_y = (world_y - transform.y) / transform.scale_y
                if self.centered:
                    local_x += self.tilemap.pixel_width / 2.0
                    local_y += self.tilemap.pixel_height / 2.0
                corners.append(self.tilemap.world_to_tile(local_x, local_y))

            margin = max(0, int(self.culling_margin)) + 2
            min_x = max(0, min(x for x, _ in corners) - margin)
            min_y = max(0, min(y for _, y in corners) - margin)
            max_x = min(self.tilemap.width - 1, max(x for x, _ in corners) + margin)
            max_y = min(self.tilemap.height - 1, max(y for _, y in corners) + margin)
            return (min_x, min_y, max_x, max_y)

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

            sprite_buckets: dict[int, list[tuple]] = {}

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

                        resolved_tile_id = self.tileset.resolve_tile(
                            cached_tile.tile_id,
                            self._animation_time,
                        )
                        if resolved_tile_id == cached_tile.tile_id:
                            uv_x = cached_tile.uv_x
                            uv_y = cached_tile.uv_y
                            uv_width = cached_tile.uv_width
                            uv_height = cached_tile.uv_height
                        else:
                            uv_x, uv_y, uv_width, uv_height = self.tileset.uv(
                                resolved_tile_id
                            )

                        depth = int(self.base_render_layer + layer.render_layer)
                        if layer.y_sort:
                            depth += int(x + y)

                        sprite_buckets.setdefault(depth, []).append(
                            (
                                float(world_x),
                                float(world_y),
                                float(tile_width),
                                float(tile_height),
                                float(transform.rotation),
                                0.5,
                                0.5,
                                float(alpha),
                                bool(flip_x),
                                bool(flip_y),
                                float(uv_x),
                                float(uv_y),
                                float(uv_width),
                                float(uv_height),
                            )
                        )

            # ======================================================
            # Bulk GPU submission
            # ======================================================

            if not sprite_buckets:
                continue

            for depth in sorted(sprite_buckets):
                rendered = renderer.sprites(
                    self.texture,
                    sprite_buckets[depth],
                    layer=depth,
                )
                self.last_rendered_tiles += rendered
