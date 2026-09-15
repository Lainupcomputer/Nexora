from __future__ import annotations

from nexora.core.game import Game
from nexora.nodes import (
    CharacterBody2D,
    NavigationAgent2D,
    TileMapNode,
)
from nexora.scene import Scene
from nexora.tilemap import (
    TileMap,
    TileMetadata,
    TileProjection,
    TileSet,
)


MAP_WIDTH = 16
MAP_HEIGHT = 16

TILE_WIDTH = 64
TILE_HEIGHT = 32

NPC_SPEED = 95.0

START_TILE = (2, 2)

TARGET_A = (13, 12)
TARGET_B = (3, 13)


class NavigationAgentExample(Game):
    def __init__(self) -> None:
        super().__init__(
            project_name="NavigationAgentExample",
            title="Nexora - NavigationAgent2D",
            width=1280,
            height=720,
            target_fps=60,
            resizable=True,
            vsync=True,
        )

        self.map_node: TileMapNode | None = None
        self.npc: CharacterBody2D | None = None
        self.agent: NavigationAgent2D | None = None

        self.target_index = 0

    # ==========================================================
    # Initialize
    # ==========================================================

    def initialize(self) -> None:
        self.scene = Scene(
            "NavigationAgentExample"
        )

        self.input.bind(
            "exit",
            "ESCAPE",
        )

        self.input.bind(
            "retarget",
            "SPACE",
        )

        # ------------------------------------------------------
        # Tileset
        #
        # 2 columns x 4 rows
        # 8 tiles total
        # 64 x 32 px per tile
        # ------------------------------------------------------

        tileset = TileSet(
            name="NavigationTiles",
            columns=2,
            rows=4,
            tile_width=TILE_WIDTH,
            tile_height=TILE_HEIGHT,
            texture_asset=(
                "world/isometric_tiles.png"
            ),
        )

        # Tile 7 will be used as a blocked tile.
        blocked_metadata = TileMetadata(
            solid=True,
        )

        tileset.set_metadata(
            7,
            blocked_metadata,
        )

        # Normal ground.
        ground_metadata = TileMetadata(
            solid=False,
        )

        for tile_id in range(7):
            tileset.set_metadata(
                tile_id,
                ground_metadata,
            )

        # ------------------------------------------------------
        # TileMap
        # ------------------------------------------------------

        tilemap = TileMap(
            name="NavigationWorld",
            width=MAP_WIDTH,
            height=MAP_HEIGHT,
            tile_width=TILE_WIDTH,
            tile_height=TILE_HEIGHT,
            projection=(
                TileProjection.ISOMETRIC
            ),
        )

        ground = tilemap.create_layer(
            "ground",
            render_layer=-100,
            y_sort=False,
        )

        # ------------------------------------------------------
        # Ground
        # ------------------------------------------------------

        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                tile_id = 0

                if x >= 8:
                    tile_id = 2

                if y >= 11:
                    tile_id = 3

                if x in (7, 8):
                    tile_id = 4

                ground.set_tile(
                    x,
                    y,
                    tile_id,
                )

        # ------------------------------------------------------
        # Navigation obstacle
        #
        # Vertical wall with one opening.
        # ------------------------------------------------------

        wall_x = 8

        for y in range(
            2,
            14,
        ):
            # Leave one opening.
            if y == 8:
                continue

            ground.set_tile(
                wall_x,
                y,
                7,
            )

        # ------------------------------------------------------
        # TileMapNode
        # ------------------------------------------------------

        self.map_node = self.scene.create_node(
            "World",
            node_type=TileMapNode,
        )

        self.map_node.set_map_from_assets(
            tilemap,
            tileset,
            self.engine.assets,
        )

        self.map_node.base_render_layer = 0

        # ------------------------------------------------------
        # CharacterBody2D
        # ------------------------------------------------------

        self.npc = self.scene.create_node(
            "NPC",
            node_type=CharacterBody2D,
        )

        start_x, start_y = (
            self.map_node.tile_world_position(
                *START_TILE
            )
        )

        self.npc.transform.x = start_x
        self.npc.transform.y = start_y

        # ------------------------------------------------------
        # NavigationAgent2D
        #
        # CharacterBody2D
        # └── NavigationAgent2D
        # ------------------------------------------------------

        self.agent = self.scene.create_node(
            "NavigationAgent",
            parent=self.npc,
            node_type=NavigationAgent2D,
        )

        self.agent.configure(
            self.map_node,
            layer_name="ground",
            allow_diagonal=False,
        )

        self.agent.waypoint_tolerance = 4.0
        self.agent.target_tolerance = 5.0

        self.agent.auto_repath = True
        self.agent.repath_interval = 0.25

        # ------------------------------------------------------
        # Callbacks
        # ------------------------------------------------------

        self.agent.connect_path_changed(
            self._on_path_changed
        )

        self.agent.connect_target_reached(
            self._on_target_reached
        )

        self.agent.connect_navigation_failed(
            self._on_navigation_failed
        )

        # ------------------------------------------------------
        # Initial target
        # ------------------------------------------------------

        self._set_target(
            TARGET_A
        )

        print("=" * 60)
        print(" Nexora NavigationAgent2D Example")
        print("=" * 60)
        print()
        print("ESC   -> Exit")
        print("SPACE -> Change target")
        print()

    # ==========================================================
    # Targets
    # ==========================================================

    def _set_target(
        self,
        tile: tuple[int, int],
    ) -> None:
        if (
            self.map_node is None
            or self.agent is None
        ):
            return

        world_x, world_y = (
            self.map_node.tile_world_position(
                *tile
            )
        )

        self.agent.set_target_position(
            world_x,
            world_y,
        )

        # request_path() is optional here because the agent
        # automatically sees the dirty target on update().
        #
        # Calling it immediately is useful for this debug example
        # because the path appears in the same frame.
        self.agent.request_path()

        print(
            "Target:",
            tile,
            "->",
            (
                round(world_x, 1),
                round(world_y, 1),
            ),
        )

    # ==========================================================
    # Agent callbacks
    # ==========================================================

    def _on_path_changed(
        self,
        agent: NavigationAgent2D,
    ) -> None:
        if agent.path is None:
            return

        print(
            "Path changed:",
            len(agent.path.tiles),
            "tiles",
        )

    def _on_target_reached(
        self,
        agent: NavigationAgent2D,
    ) -> None:
        print(
            "Target reached:",
            agent.target_position,
        )

    def _on_navigation_failed(
        self,
        agent: NavigationAgent2D,
    ) -> None:
        print(
            "Navigation failed:",
            agent.target_position,
        )

    # ==========================================================
    # Update
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        if self.input.action(
            "exit"
        ).pressed:
            self.stop()
            return

        if self.input.action(
            "retarget"
        ).pressed:
            self.target_index = (
                1 - self.target_index
            )

            target = (
                TARGET_A
                if self.target_index == 0
                else TARGET_B
            )

            self._set_target(
                target
            )

        # ------------------------------------------------------
        # Let Scene/Nodes update first.
        #
        # NavigationAgent2D calculates / advances its path here.
        # ------------------------------------------------------

        super().update(
            delta_time
        )

        if (
            self.npc is None
            or self.agent is None
        ):
            return

        # ------------------------------------------------------
        # NavigationAgent2D does NOT move the CharacterBody2D.
        #
        # We ask it for the desired velocity and apply that
        # ourselves.
        # ------------------------------------------------------

        velocity_x, velocity_y = (
            self.agent.desired_velocity(
                NPC_SPEED
            )
        )

        self.npc.velocity.x = velocity_x
        self.npc.velocity.y = velocity_y

        self.npc.move_and_slide(
            delta_time
        )

        # Stop the body when navigation is finished.
        if (
            self.agent.target_reached
            or self.agent.navigation_failed
        ):
            self.npc.velocity.x = 0.0
            self.npc.velocity.y = 0.0

    # ==========================================================
    # Render
    # ==========================================================

    def render(
        self,
        interpolation: float,
    ) -> None:
        # First render the Scene.
        #
        # TileMapNode gets rendered here automatically.
        super().render(
            interpolation
        )

        if (
            self.npc is None
            or self.agent is None
        ):
            return

        npc_x, npc_y = (
            self.npc.world_position
        )

        # ------------------------------------------------------
        # Debug path
        # ------------------------------------------------------

        previous_x = npc_x
        previous_y = npc_y

        for waypoint_x, waypoint_y in (
            self.agent.remaining_waypoints
        ):
            self.renderer.line(
                previous_x,
                previous_y,
                waypoint_x,
                waypoint_y,
                width=3.0,
                color=(
                    0.15,
                    0.8,
                    1.0,
                    0.9,
                ),
                layer=100,
            )

            self.renderer.circle(
                waypoint_x,
                waypoint_y,
                8.0,
                color=(
                    0.15,
                    0.8,
                    1.0,
                    1.0,
                ),
                layer=101,
            )

            previous_x = waypoint_x
            previous_y = waypoint_y

        # ------------------------------------------------------
        # Target marker
        # ------------------------------------------------------

        if self.agent.target_position is not None:
            target_x, target_y = (
                self.agent.target_position
            )

            self.renderer.circle(
                target_x,
                target_y,
                20.0,
                color=(
                    1.0,
                    0.2,
                    0.2,
                    0.45,
                ),
                layer=110,
            )

            self.renderer.circle(
                target_x,
                target_y,
                7.0,
                color=(
                    1.0,
                    0.2,
                    0.2,
                    1.0,
                ),
                layer=111,
            )

        # ------------------------------------------------------
        # Current waypoint
        # ------------------------------------------------------

        waypoint = (
            self.agent.current_waypoint
        )

        if waypoint is not None:
            self.renderer.circle(
                waypoint[0],
                waypoint[1],
                13.0,
                color=(
                    1.0,
                    0.85,
                    0.1,
                    1.0,
                ),
                layer=115,
            )

        # ------------------------------------------------------
        # NPC
        #
        # For this navigation test we intentionally use a simple
        # debug shape instead of requiring another sprite asset.
        # ------------------------------------------------------

        self.renderer.circle(
            npc_x,
            npc_y,
            24.0,
            color=(
                0.2,
                1.0,
                0.35,
                1.0,
            ),
            layer=120,
        )

        self.renderer.circle(
            npc_x,
            npc_y,
            8.0,
            color=(
                0.05,
                0.15,
                0.07,
                1.0,
            ),
            layer=121,
        )


if __name__ == "__main__":
    NavigationAgentExample().run()