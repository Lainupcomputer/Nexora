from __future__ import annotations

import sdl3

from nexora.core.game import Game
from nexora.nodes import TileMapNode
from nexora.rendering.gpu.texture import GPUTexture
from nexora.scene import Scene
from nexora.tilemap import (
    TileMap,
    TileSet,
)


class TileMapTest(Game):
    # ==============================================================
    # Tileset
    # ==============================================================

    TILE_WIDTH = 64
    TILE_HEIGHT = 64

    TILESET_COLUMNS = 4
    TILESET_ROWS = 4

    # ==============================================================
    # Map
    # ==============================================================

    MAP_WIDTH = 100
    MAP_HEIGHT = 100

    MOVE_STEP = 128.0

    def __init__(
        self,
    ) -> None:
        super().__init__()

        # ======================================================
        # Scene
        # ======================================================

        self.scene = Scene(
            "TileMapTest"
        )

        # ======================================================
        # Runtime resources
        # ======================================================

        self.texture: GPUTexture | None = None

        self.tilemap: TileMap | None = None
        self.tileset: TileSet | None = None

        self.map_node: TileMapNode | None = None

        # ======================================================
        # Debug
        # ======================================================

        self._last_visible_tiles = -1
        self._last_rendered_tiles = -1

    # ==============================================================
    # Initialize
    # ==============================================================

    def initialize(
        self,
    ) -> None:
        print("=" * 60)
        print(" Nexora TileMap GPU Test")
        print("=" * 60)
        print()

        # ----------------------------------------------------------
        # Create generated tileset texture
        # ----------------------------------------------------------

        texture_width = (
            self.TILE_WIDTH
            * self.TILESET_COLUMNS
        )

        texture_height = (
            self.TILE_HEIGHT
            * self.TILESET_ROWS
        )

        pixels = (
            self._create_tileset_pixels()
        )

        self.texture = GPUTexture(
            self.engine.gpu_context.device,
            texture_width,
            texture_height,
            data=pixels,
            bytes_per_pixel=4,
        )

        # ----------------------------------------------------------
        # TileSet
        # ----------------------------------------------------------

        self.tileset = TileSet(
            name="GeneratedTestTiles",
            columns=self.TILESET_COLUMNS,
            rows=self.TILESET_ROWS,
            tile_width=self.TILE_WIDTH,
            tile_height=self.TILE_HEIGHT,
        )

        # ----------------------------------------------------------
        # TileMap
        # ----------------------------------------------------------

        self.tilemap = TileMap(
            name="TestMap",
            width=self.MAP_WIDTH,
            height=self.MAP_HEIGHT,
            tile_width=self.TILE_WIDTH,
            tile_height=self.TILE_HEIGHT,
        )

        # ----------------------------------------------------------
        # Ground layer
        # ----------------------------------------------------------

        ground = (
            self.tilemap.create_layer(
                "ground"
            )
        )

        # Fill complete map with a repeating pattern.

        for y in range(
            self.MAP_HEIGHT
        ):
            for x in range(
                self.MAP_WIDTH
            ):
                tile_id = (
                    (
                        x
                        + y
                    )
                    % 4
                )

                ground.set_tile(
                    x,
                    y,
                    tile_id,
                )

        # ----------------------------------------------------------
        # Detail layer
        # ----------------------------------------------------------

        details = (
            self.tilemap.create_layer(
                "details"
            )
        )

        for y in range(
            0,
            self.MAP_HEIGHT,
            5,
        ):
            for x in range(
                0,
                self.MAP_WIDTH,
                5,
            ):
                tile_id = (
                    4
                    + (
                        (
                            x // 5
                            + y // 5
                        )
                        % 4
                    )
                )

                details.set_tile(
                    x,
                    y,
                    tile_id,
                )

        # ----------------------------------------------------------
        # Object layer
        # ----------------------------------------------------------

        objects = (
            self.tilemap.create_layer(
                "objects"
            )
        )

        # A diagonal pattern through the entire map.

        for index in range(
            min(
                self.MAP_WIDTH,
                self.MAP_HEIGHT,
            )
        ):
            if index % 3 != 0:
                continue

            tile_id = (
                8
                + (
                    index
                    % 4
                )
            )

            objects.set_tile(
                index,
                index,
                tile_id,
            )

        # ----------------------------------------------------------
        # Foreground layer
        # ----------------------------------------------------------

        foreground = (
            self.tilemap.create_layer(
                "foreground"
            )
        )

        # Sparse final layer using last four tiles.

        for y in range(
            2,
            self.MAP_HEIGHT,
            11,
        ):
            for x in range(
                2,
                self.MAP_WIDTH,
                11,
            ):
                tile_id = (
                    12
                    + (
                        (
                            x
                            + y
                        )
                        % 4
                    )
                )

                foreground.set_tile(
                    x,
                    y,
                    tile_id,
                )

        # ----------------------------------------------------------
        # TileMapNode
        # ----------------------------------------------------------

        node = (
            self.scene.create_node(
                "TestTileMap",
                node_type=TileMapNode,
            )
        )

        assert isinstance(
            node,
            TileMapNode,
        )

        self.map_node = node

        self.map_node.set_map(
            self.tilemap,
            self.tileset,
            self.texture,
        )

        # Map center starts in screen center.
        self.map_node.transform.x = 0.0
        self.map_node.transform.y = 0.0

        self.map_node.centered = True

        self.map_node.culling_enabled = True
        self.map_node.culling_margin = 1

        # ----------------------------------------------------------
        # Information
        # ----------------------------------------------------------

        print(
            "Generated TileSet:"
        )

        print(
            f"  Texture: "
            f"{texture_width} x "
            f"{texture_height}"
        )

        print(
            f"  Grid: "
            f"{self.TILESET_COLUMNS} x "
            f"{self.TILESET_ROWS}"
        )

        print(
            f"  Tile size: "
            f"{self.TILE_WIDTH} x "
            f"{self.TILE_HEIGHT}"
        )

        print(
            f"  Tiles: "
            f"{self.tileset.tile_count}"
        )

        print()

        print(
            "TileMap:"
        )

        print(
            f"  Map: "
            f"{self.MAP_WIDTH} x "
            f"{self.MAP_HEIGHT}"
        )

        print(
            f"  Pixel size: "
            f"{self.tilemap.pixel_width} x "
            f"{self.tilemap.pixel_height}"
        )

        print(
            f"  Layers: "
            f"{self.tilemap.layer_names}"
        )

        print()

        print(
            "Expected:"
        )

        print(
            "  A colorful tiled world should be visible."
        )

        print(
            "  The full map is much larger than the window."
        )

        print(
            "  Only visible tiles should be rendered."
        )

        print(
            "  Moving the map should update the culling area."
        )

        print()

        print(
            "Controls:"
        )

        print(
            "  LEFT / A   -> move map right"
        )

        print(
            "  RIGHT / D  -> move map left"
        )

        print(
            "  UP / W     -> move map down"
        )

        print(
            "  DOWN / S   -> move map up"
        )

        print()

        print(
            "  C -> toggle culling"
        )

        print(
            "  1 -> toggle ground layer"
        )

        print(
            "  2 -> toggle details layer"
        )

        print(
            "  3 -> toggle objects layer"
        )

        print(
            "  4 -> toggle foreground layer"
        )

        print()

        print(
            "  R -> reset map position"
        )

        print(
            "  ESC -> close"
        )

        print()

    # ==============================================================
    # Generate TileSet
    # ==============================================================

    def _create_tileset_pixels(
        self,
    ) -> bytes:
        """
        Generate a 4x4 test TileSet.

        Every tile receives:

            - unique base color
            - white border
            - black inner marker
            - marker count based on tile ID

        This makes UV errors immediately visible.
        """

        width = (
            self.TILE_WIDTH
            * self.TILESET_COLUMNS
        )

        height = (
            self.TILE_HEIGHT
            * self.TILESET_ROWS
        )

        pixels = bytearray(
            width
            * height
            * 4
        )

        colors = (
            (
                55,
                120,
                65,
                255,
            ),
            (
                75,
                150,
                80,
                255,
            ),
            (
                90,
                110,
                160,
                255,
            ),
            (
                125,
                100,
                70,
                255,
            ),

            (
                180,
                120,
                60,
                255,
            ),
            (
                175,
                70,
                60,
                255,
            ),
            (
                80,
                150,
                160,
                255,
            ),
            (
                145,
                80,
                155,
                255,
            ),

            (
                200,
                165,
                70,
                255,
            ),
            (
                80,
                105,
                190,
                255,
            ),
            (
                170,
                75,
                120,
                255,
            ),
            (
                60,
                170,
                140,
                255,
            ),

            (
                125,
                125,
                125,
                255,
            ),
            (
                200,
                100,
                75,
                255,
            ),
            (
                105,
                190,
                90,
                255,
            ),
            (
                190,
                190,
                190,
                255,
            ),
        )

        # ----------------------------------------------------------
        # Tiles
        # ----------------------------------------------------------

        for tile_id in range(
            self.TILESET_COLUMNS
            * self.TILESET_ROWS
        ):
            column = (
                tile_id
                % self.TILESET_COLUMNS
            )

            row = (
                tile_id
                // self.TILESET_COLUMNS
            )

            tile_start_x = (
                column
                * self.TILE_WIDTH
            )

            tile_start_y = (
                row
                * self.TILE_HEIGHT
            )

            (
                base_r,
                base_g,
                base_b,
                base_a,
            ) = colors[
                tile_id
            ]

            for local_y in range(
                self.TILE_HEIGHT
            ):
                for local_x in range(
                    self.TILE_WIDTH
                ):
                    x = (
                        tile_start_x
                        + local_x
                    )

                    y = (
                        tile_start_y
                        + local_y
                    )

                    r = base_r
                    g = base_g
                    b = base_b
                    a = base_a

                    # ------------------------------------------
                    # White border
                    # ------------------------------------------

                    if (
                        local_x < 2
                        or local_y < 2
                        or local_x
                        >= self.TILE_WIDTH - 2
                        or local_y
                        >= self.TILE_HEIGHT - 2
                    ):
                        r = 245
                        g = 245
                        b = 245

                    # ------------------------------------------
                    # Dark center
                    # ------------------------------------------

                    center_min_x = (
                        self.TILE_WIDTH
                        // 2
                        - 5
                    )

                    center_max_x = (
                        self.TILE_WIDTH
                        // 2
                        + 5
                    )

                    center_min_y = (
                        self.TILE_HEIGHT
                        // 2
                        - 5
                    )

                    center_max_y = (
                        self.TILE_HEIGHT
                        // 2
                        + 5
                    )

                    if (
                        center_min_x
                        <= local_x
                        < center_max_x
                        and
                        center_min_y
                        <= local_y
                        < center_max_y
                    ):
                        r = 20
                        g = 20
                        b = 25

                    # ------------------------------------------
                    # Tile-ID markers
                    # ------------------------------------------

                    marker_count = (
                        tile_id
                        % 4
                    ) + 1

                    for marker in range(
                        marker_count
                    ):
                        marker_x = (
                            7
                            + marker
                            * 10
                        )

                        if (
                            marker_x
                            <= local_x
                            < marker_x + 5
                            and
                            7
                            <= local_y
                            < 17
                        ):
                            r = 255
                            g = 255
                            b = 255

                    # ------------------------------------------
                    # RGBA
                    # ------------------------------------------

                    offset = (
                        (
                            y
                            * width
                            + x
                        )
                        * 4
                    )

                    pixels[
                        offset
                    ] = r

                    pixels[
                        offset + 1
                    ] = g

                    pixels[
                        offset + 2
                    ] = b

                    pixels[
                        offset + 3
                    ] = a

        return bytes(
            pixels
        )

    # ==============================================================
    # Update
    # ==============================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        super().update(
            delta_time
        )

        if self.map_node is None:
            return

        # ----------------------------------------------------------
        # Print statistics only when they change.
        # ----------------------------------------------------------

        visible = (
            self.map_node.last_visible_tiles
        )

        rendered = (
            self.map_node.last_rendered_tiles
        )

        if (
            visible
            != self._last_visible_tiles
            or rendered
            != self._last_rendered_tiles
        ):
            print(
                "[TileMap] "
                f"visible area = {visible}, "
                f"rendered = {rendered}, "
                f"position = "
                f"("
                f"{self.map_node.transform.x:.1f}, "
                f"{self.map_node.transform.y:.1f}"
                f")"
            )

            self._last_visible_tiles = (
                visible
            )

            self._last_rendered_tiles = (
                rendered
            )

    # ==============================================================
    # Input
    # ==============================================================

    def handle_event(
        self,
        event,
    ) -> None:
        if (
            event.type
            != sdl3.SDL_EVENT_KEY_DOWN
        ):
            return

        if getattr(
            event.key,
            "repeat",
            False,
        ):
            return

        key = (
            event.key.key
        )

        # ----------------------------------------------------------
        # Exit
        # ----------------------------------------------------------

        if key == sdl3.SDLK_ESCAPE:
            self.stop()
            return

        if (
            self.map_node is None
            or self.tilemap is None
        ):
            return

        # ----------------------------------------------------------
        # Movement
        #
        # We move the map itself.
        #
        # This effectively behaves like moving a camera in the
        # opposite direction and is enough to verify culling.
        # ----------------------------------------------------------

        if (
            key == sdl3.SDLK_LEFT
            or key == sdl3.SDLK_A
        ):
            self.map_node.transform.x += (
                self.MOVE_STEP
            )

            return

        if (
            key == sdl3.SDLK_RIGHT
            or key == sdl3.SDLK_D
        ):
            self.map_node.transform.x -= (
                self.MOVE_STEP
            )

            return

        if (
            key == sdl3.SDLK_UP
            or key == sdl3.SDLK_W
        ):
            self.map_node.transform.y += (
                self.MOVE_STEP
            )

            return

        if (
            key == sdl3.SDLK_DOWN
            or key == sdl3.SDLK_S
        ):
            self.map_node.transform.y -= (
                self.MOVE_STEP
            )

            return

        # ----------------------------------------------------------
        # Reset
        # ----------------------------------------------------------

        if key == sdl3.SDLK_R:
            self.map_node.transform.x = 0.0
            self.map_node.transform.y = 0.0

            print(
                "[TileMap] position reset"
            )

            return

        # ----------------------------------------------------------
        # Culling
        # ----------------------------------------------------------

        if key == sdl3.SDLK_C:
            self.map_node.culling_enabled = (
                not
                self.map_node.culling_enabled
            )

            print(
                "[TileMap] "
                f"culling = "
                f"{self.map_node.culling_enabled}"
            )

            return

        # ----------------------------------------------------------
        # Layers
        # ----------------------------------------------------------

        if key == sdl3.SDLK_1:
            self._toggle_layer(
                "ground"
            )

            return

        if key == sdl3.SDLK_2:
            self._toggle_layer(
                "details"
            )

            return

        if key == sdl3.SDLK_3:
            self._toggle_layer(
                "objects"
            )

            return

        if key == sdl3.SDLK_4:
            self._toggle_layer(
                "foreground"
            )

            return

    # ==============================================================
    # Layer helper
    # ==============================================================

    def _toggle_layer(
        self,
        name: str,
    ) -> None:
        if self.tilemap is None:
            return

        layer = (
            self.tilemap.require_layer(
                name
            )
        )

        layer.visible = (
            not layer.visible
        )

        print(
            f"[Layer] "
            f"{name} "
            f"visible = "
            f"{layer.visible}"
        )

    # ==============================================================
    # Shutdown
    # ==============================================================

    def shutdown(
        self,
    ) -> None:
        # TileMapNode references the texture,
        # but does not own it.

        if self.texture is not None:
            self.texture.destroy()

            self.texture = None

        super().shutdown()


def main() -> None:
    game = TileMapTest()

    game.run()


if __name__ == "__main__":
    main()