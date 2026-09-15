from __future__ import annotations

from nexora.core.game import Game
from nexora.nodes import TileMapNode
from nexora.scene import Scene
from nexora.tilemap import (
    TileMap,
    TileProjection,
    TileSet,
)


class IsometricTileMapExample(Game):
    def initialize(self) -> None:
        # self.scene registriert/aktiviert die Scene bereits.
        self.scene = Scene(
            "IsoTileMapV2"
        )

        # ------------------------------------------------------
        # Tileset
        #
        # 2 columns × 4 rows
        # 8 tiles total
        # each tile = 64×32
        #
        # complete texture:
        # 128×128 px
        # ------------------------------------------------------

        tileset = TileSet(
            name="GroundTiles",
            columns=2,
            rows=4,
            tile_width=64,
            tile_height=32,
            texture_asset=(
                "world/isometric_tiles.png"
            ),
        )

        # ------------------------------------------------------
        # TileMap
        # ------------------------------------------------------

        tilemap = TileMap(
            name="IsoWorld",
            width=16,
            height=16,
            tile_width=64,
            tile_height=32,
            projection=(
                TileProjection.ISOMETRIC
            ),
        )

        # ------------------------------------------------------
        # Ground layer
        # ------------------------------------------------------

        ground = tilemap.create_layer(
            "ground",
            render_layer=-100,
            y_sort=False,
        )

        # ------------------------------------------------------
        # Create some larger terrain areas instead of a noisy
        # checkerboard so the isometric map is easier to judge.
        #
        # Tile IDs:
        #
        # 0 grass
        # 1 dry grass
        # 2 dirt
        # 3 sand
        # 4 cobblestone
        # 5 stone slabs
        # 6 concrete
        # 7 rust / metal
        # ------------------------------------------------------

        for y in range(
            tilemap.height
        ):
            for x in range(
                tilemap.width
            ):
                # Grass area
                tile_id = 0

                # Dirt
                if x >= 8:
                    tile_id = 2

                # Sand
                if y >= 10:
                    tile_id = 3

                # Cobblestone path
                if (
                    x == 7
                    or x == 8
                ):
                    tile_id = 4

                # Stone area
                if (
                    x >= 10
                    and y <= 5
                ):
                    tile_id = 5

                # Concrete area
                if (
                    x <= 4
                    and y >= 10
                ):
                    tile_id = 6

                # Metal test area
                if (
                    x >= 11
                    and y >= 11
                ):
                    tile_id = 7

                ground.set_tile(
                    x,
                    y,
                    tile_id,
                )

        # ------------------------------------------------------
        # TileMap node
        # ------------------------------------------------------

        node = self.scene.create_node(
            "World",
            node_type=TileMapNode,
        )

        node.set_map_from_assets(
            tilemap,
            tileset,
            self.engine.assets,
        )

        node.base_render_layer = 0

        # ------------------------------------------------------
        # Input
        # ------------------------------------------------------

        self.input.bind(
            "exit",
            "ESCAPE",
        )

    def update(
        self,
        delta_time: float,
    ) -> None:
        if (
            self.input
            .action("exit")
            .pressed
        ):
            self.stop()


if __name__ == "__main__":
    IsometricTileMapExample().run()