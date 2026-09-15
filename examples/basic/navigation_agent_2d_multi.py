from __future__ import annotations

from dataclasses import dataclass

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


MAP_WIDTH = 18
MAP_HEIGHT = 14

TILE_WIDTH = 64
TILE_HEIGHT = 32

NPC_SPEED = 85.0


@dataclass(slots=True)
class AgentEntry:
    body: CharacterBody2D
    agent: NavigationAgent2D

    color: tuple[
        float,
        float,
        float,
        float,
    ]

    start_tile: tuple[int, int]
    target_tile: tuple[int, int]


class MultiNavigationExample(Game):
    def __init__(self) -> None:
        super().__init__(
            project_name="MultiNavigationExample",
            title="Nexora - Multi Agent Local Avoidance",
            width=1280,
            height=720,
            target_fps=60,
            resizable=True,
            vsync=True,
        )

        self.map_node: TileMapNode | None = None

        self.agents: list[
            AgentEntry
        ] = []

        self.target_mode = 0

    # ==========================================================
    # INITIALIZE
    # ==========================================================

    def initialize(self) -> None:
        self.scene = Scene(
            "MultiNavigationExample"
        )

        # ------------------------------------------------------
        # INPUT
        # ------------------------------------------------------

        self.input.bind(
            "exit",
            "ESCAPE",
        )

        self.input.bind(
            "retarget",
            "SPACE",
        )

        self.input.bind(
            "reset",
            "R",
        )

        # ------------------------------------------------------
        # TILESET
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

        # ------------------------------------------------------
        # TILES 0 - 6 = WALKABLE
        #
        # TileMetadata currently uses solid directly.
        # There is no walkable constructor argument.
        # ------------------------------------------------------

        for tile_id in range(7):
            tileset.set_metadata(
                tile_id,
                TileMetadata(
                    solid=False,
                ),
            )

        # ------------------------------------------------------
        # TILE 7 = BLOCKED
        # ------------------------------------------------------

        tileset.set_metadata(
            7,
            TileMetadata(
                solid=True,
            ),
        )

        # ------------------------------------------------------
        # TILEMAP
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
        # GROUND
        # ------------------------------------------------------

        for y in range(
            MAP_HEIGHT
        ):
            for x in range(
                MAP_WIDTH
            ):
                tile_id = 0

                if x >= 9:
                    tile_id = 2

                if y >= 9:
                    tile_id = 3

                if x in (
                    8,
                    9,
                ):
                    tile_id = 4

                ground.set_tile(
                    x,
                    y,
                    tile_id,
                )

        # ------------------------------------------------------
        # WALL
        #
        # Two vertical wall sections.
        #
        # In the center there is an opening so all agents are
        # forced through roughly the same area.
        # ------------------------------------------------------

        for y in range(
            1,
            MAP_HEIGHT - 1,
        ):
            if y in (
                5,
                6,
                7,
                8,
            ):
                continue

            ground.set_tile(
                8,
                y,
                7,
            )

            ground.set_tile(
                9,
                y,
                7,
            )

        # ------------------------------------------------------
        # TILEMAP NODE
        # ------------------------------------------------------

        self.map_node = (
            self.scene.create_node(
                "World",
                node_type=TileMapNode,
            )
        )

        self.map_node.set_map_from_assets(
            tilemap,
            tileset,
            self.engine.assets,
        )

        self.map_node.base_render_layer = 0

        # ------------------------------------------------------
        # CREATE AGENTS
        # ------------------------------------------------------

        self._create_agents()

        print("=" * 70)
        print(
            " Nexora Multi Agent Local Avoidance Example"
        )
        print("=" * 70)
        print()
        print(
            "ESC   -> Exit"
        )
        print(
            "SPACE -> Swap targets"
        )
        print(
            "R     -> Reset agents"
        )
        print()

    # ==========================================================
    # CREATE AGENTS
    # ==========================================================

    def _create_agents(
        self,
    ) -> None:
        if self.map_node is None:
            return

        definitions = [
            (
                "AgentA",
                (2, 5),
                (15, 5),
                (
                    0.20,
                    1.00,
                    0.35,
                    1.0,
                ),
            ),
            (
                "AgentB",
                (2, 6),
                (15, 6),
                (
                    0.20,
                    0.75,
                    1.00,
                    1.0,
                ),
            ),
            (
                "AgentC",
                (2, 7),
                (15, 7),
                (
                    1.00,
                    0.80,
                    0.20,
                    1.0,
                ),
            ),
            (
                "AgentD",
                (15, 5),
                (2, 5),
                (
                    1.00,
                    0.25,
                    0.25,
                    1.0,
                ),
            ),
            (
                "AgentE",
                (15, 6),
                (2, 6),
                (
                    0.85,
                    0.30,
                    1.00,
                    1.0,
                ),
            ),
            (
                "AgentF",
                (15, 7),
                (2, 7),
                (
                    1.00,
                    0.50,
                    0.15,
                    1.0,
                ),
            ),
        ]

        for (
            name,
            start_tile,
            target_tile,
            color,
        ) in definitions:
            # --------------------------------------------------
            # BODY
            # --------------------------------------------------

            body = (
                self.scene.create_node(
                    name,
                    node_type=CharacterBody2D,
                )
            )

            start_x, start_y = (
                self.map_node
                .tile_world_position(
                    *start_tile
                )
            )

            body.transform.x = start_x
            body.transform.y = start_y

            # --------------------------------------------------
            # NAVIGATION AGENT
            # --------------------------------------------------

            agent = (
                self.scene.create_node(
                    f"{name}Navigation",
                    parent=body,
                    node_type=(
                        NavigationAgent2D
                    ),
                )
            )

            agent.configure(
                self.map_node,
                layer_name="ground",
                allow_diagonal=False,
            )

            # --------------------------------------------------
            # NAVIGATION SETTINGS
            # --------------------------------------------------

            agent.waypoint_tolerance = (
                5.0
            )

            agent.target_tolerance = (
                7.0
            )

            agent.auto_repath = True

            agent.repath_interval = (
                0.20
            )

            # --------------------------------------------------
            # LOCAL AVOIDANCE SETTINGS
            # --------------------------------------------------

            agent.avoidance_enabled = (
                True
            )

            agent.avoidance_radius = (
                15.0
            )

            agent.avoidance_neighbor_distance = (
                110.0
            )

            agent.avoidance_time_horizon = (
                1.25
            )

            agent.avoidance_strength = (
                1.0
            )

            # --------------------------------------------------
            # INITIAL TARGET
            # --------------------------------------------------

            target_x, target_y = (
                self.map_node
                .tile_world_position(
                    *target_tile
                )
            )

            agent.set_target_position(
                target_x,
                target_y,
            )

            agent.request_path()

            self.agents.append(
                AgentEntry(
                    body=body,
                    agent=agent,
                    color=color,
                    start_tile=start_tile,
                    target_tile=target_tile,
                )
            )

    # ==========================================================
    # SET TARGET
    # ==========================================================

    def _set_target(
        self,
        entry: AgentEntry,
        tile: tuple[int, int],
    ) -> None:
        if self.map_node is None:
            return

        x, y = (
            self.map_node
            .tile_world_position(
                *tile
            )
        )

        entry.target_tile = tile

        entry.agent.set_target_position(
            x,
            y,
        )

        entry.agent.request_path()

    # ==========================================================
    # SWAP TARGETS
    # ==========================================================

    def _swap_targets(
        self,
    ) -> None:
        self.target_mode = (
            1 - self.target_mode
        )

        if self.target_mode == 0:
            targets = [
                (15, 5),
                (15, 6),
                (15, 7),
                (2, 5),
                (2, 6),
                (2, 7),
            ]

        else:
            targets = [
                (2, 7),
                (2, 6),
                (2, 5),
                (15, 7),
                (15, 6),
                (15, 5),
            ]

        for entry, target in zip(
            self.agents,
            targets,
        ):
            self._set_target(
                entry,
                target,
            )

    # ==========================================================
    # RESET
    # ==========================================================

    def _reset_agents(
        self,
    ) -> None:
        if self.map_node is None:
            return

        self.target_mode = 0

        targets = [
            (15, 5),
            (15, 6),
            (15, 7),
            (2, 5),
            (2, 6),
            (2, 7),
        ]

        for entry, target in zip(
            self.agents,
            targets,
        ):
            x, y = (
                self.map_node
                .tile_world_position(
                    *entry.start_tile
                )
            )

            entry.body.transform.x = x
            entry.body.transform.y = y

            entry.body.velocity.x = 0.0
            entry.body.velocity.y = 0.0

            self._set_target(
                entry,
                target,
            )

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        # ------------------------------------------------------
        # INPUT
        # ------------------------------------------------------

        if (
            self.input
            .action("exit")
            .pressed
        ):
            self.stop()
            return

        if (
            self.input
            .action("retarget")
            .pressed
        ):
            self._swap_targets()
            self.logger.info("Test Info")
            self.logger.warning("Test Warning")
            self.logger.error("Test Error")

        if (
            self.input
            .action("reset")
            .pressed
        ):
            self._reset_agents()

        # ------------------------------------------------------
        # UPDATE NODE TREE
        #
        # NavigationAgent2D publishes its current state into the
        # shared avoidance state during update().
        # ------------------------------------------------------

        super().update(
            delta_time
        )

        # ------------------------------------------------------
        # MOVE AGENTS
        # ------------------------------------------------------

        for entry in self.agents:
            body = entry.body
            agent = entry.agent

            if (
                agent.target_reached
                or agent.navigation_failed
            ):
                body.velocity.x = 0.0
                body.velocity.y = 0.0

                continue

            velocity_x, velocity_y = (
                agent.desired_velocity(
                    NPC_SPEED
                )
            )

            body.velocity.x = velocity_x
            body.velocity.y = velocity_y

            body.move_and_slide(
                delta_time
            )

    # ==========================================================
    # RENDER
    # ==========================================================

    def render(
        self,
        interpolation: float,
    ) -> None:
        super().render(
            interpolation
        )

        for entry in self.agents:
            body = entry.body
            agent = entry.agent

            x, y = (
                body.world_position
            )

            # --------------------------------------------------
            # PATH
            # --------------------------------------------------

            previous_x = x
            previous_y = y

            for (
                waypoint_x,
                waypoint_y,
            ) in agent.remaining_waypoints:
                self.renderer.line(
                    previous_x,
                    previous_y,
                    waypoint_x,
                    waypoint_y,
                    width=2.0,
                    color=(
                        entry.color[0],
                        entry.color[1],
                        entry.color[2],
                        0.35,
                    ),
                    layer=100,
                )

                previous_x = waypoint_x
                previous_y = waypoint_y

            # --------------------------------------------------
            # AVOIDANCE RADIUS
            # --------------------------------------------------

            self.renderer.circle(
                x,
                y,
                agent.avoidance_radius,
                color=(
                    entry.color[0],
                    entry.color[1],
                    entry.color[2],
                    0.12,
                ),
                layer=105,
            )

            # --------------------------------------------------
            # PREFERRED VELOCITY
            #
            # Yellow = pure navigation direction.
            # --------------------------------------------------

            preferred_x, preferred_y = (
                agent.preferred_velocity(
                    NPC_SPEED
                )
            )

            self.renderer.line(
                x,
                y,
                (
                    x
                    + preferred_x
                    * 0.35
                ),
                (
                    y
                    + preferred_y
                    * 0.35
                ),
                width=2.0,
                color=(
                    1.0,
                    0.85,
                    0.10,
                    0.85,
                ),
                layer=110,
            )

            # --------------------------------------------------
            # DESIRED VELOCITY
            #
            # White = navigation + local avoidance.
            # --------------------------------------------------

            desired_x, desired_y = (
                agent.desired_velocity(
                    NPC_SPEED
                )
            )

            self.renderer.line(
                x,
                y,
                (
                    x
                    + desired_x
                    * 0.35
                ),
                (
                    y
                    + desired_y
                    * 0.35
                ),
                width=3.0,
                color=(
                    1.0,
                    1.0,
                    1.0,
                    1.0,
                ),
                layer=111,
            )

            # --------------------------------------------------
            # TARGET
            # --------------------------------------------------

            if (
                agent.target_position
                is not None
            ):
                target_x, target_y = (
                    agent.target_position
                )

                self.renderer.circle(
                    target_x,
                    target_y,
                    10.0,
                    color=(
                        entry.color[0],
                        entry.color[1],
                        entry.color[2],
                        0.60,
                    ),
                    layer=115,
                )

            # --------------------------------------------------
            # AGENT BODY
            # --------------------------------------------------

            self.renderer.circle(
                x,
                y,
                16.0,
                color=entry.color,
                layer=120,
            )

            self.renderer.circle(
                x,
                y,
                6.0,
                color=(
                    0.06,
                    0.06,
                    0.08,
                    1.0,
                ),
                layer=121,
            )


if __name__ == "__main__":
    MultiNavigationExample().run()