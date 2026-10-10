from __future__ import annotations

from typing import Any

from nexora.nodes.navigation.navigation_agent_2d import NavigationAgent2D
from nexora.nodes.navigation.navigation_obstacle_2d import NavigationObstacle2D


def register_navigation_nodes(registry) -> None:
    # ==========================================================
    # NavigationAgent2D
    # ==========================================================

    def dump_navigation_agent(
        node: NavigationAgent2D,
    ) -> dict[str, Any]:
        return {
            "map_node_name": (
                node.map_node_name
            ),
            "layer_name": str(
                node.layer_name
            ),
            "allow_diagonal": bool(
                node.allow_diagonal
            ),
            "allow_corner_cutting": bool(
                node.allow_corner_cutting
            ),
            "empty_walkable": bool(
                node.empty_walkable
            ),
            "default_cost": float(
                node.default_cost
            ),
            "cache_paths": bool(
                node.cache_paths
            ),
            "waypoint_tolerance": float(
                node.waypoint_tolerance
            ),
            "target_tolerance": float(
                node.target_tolerance
            ),
            "auto_repath": bool(
                node.auto_repath
            ),
            "repath_interval": float(
                node.repath_interval
            ),
            "avoidance_enabled": bool(
                node.avoidance_enabled
            ),
            "avoidance_radius": float(
                node.avoidance_radius
            ),
            "avoidance_neighbor_distance": float(
                node.avoidance_neighbor_distance
            ),
            "avoidance_time_horizon": float(
                node.avoidance_time_horizon
            ),
            "avoidance_strength": float(
                node.avoidance_strength
            ),
            "target_position": (
                node.target_position
            ),
        }

    def load_navigation_agent(
        node: NavigationAgent2D,
        state: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        map_name = state.get(
            "map_node_name"
        )

        node.map_node_name = (
            None
            if map_name is None
            else str(map_name)
        )

        node.layer_name = str(
            state.get(
                "layer_name",
                "ground",
            )
        )

        node.allow_diagonal = bool(
            state.get(
                "allow_diagonal",
                False,
            )
        )

        node.allow_corner_cutting = bool(
            state.get(
                "allow_corner_cutting",
                False,
            )
        )

        node.empty_walkable = bool(
            state.get(
                "empty_walkable",
                True,
            )
        )

        node.default_cost = float(
            state.get(
                "default_cost",
                1.0,
            )
        )

        node.cache_paths = bool(
            state.get(
                "cache_paths",
                True,
            )
        )

        node.waypoint_tolerance = float(
            state.get(
                "waypoint_tolerance",
                4.0,
            )
        )

        node.target_tolerance = float(
            state.get(
                "target_tolerance",
                4.0,
            )
        )

        node.auto_repath = bool(
            state.get(
                "auto_repath",
                True,
            )
        )

        node.repath_interval = float(
            state.get(
                "repath_interval",
                0.25,
            )
        )

        node.avoidance_enabled = bool(
            state.get(
                "avoidance_enabled",
                True,
            )
        )

        node.avoidance_radius = max(
            float(
                state.get(
                    "avoidance_radius",
                    12.0,
                )
            ),
            0.0,
        )

        node.avoidance_neighbor_distance = max(
            float(
                state.get(
                    "avoidance_neighbor_distance",
                    64.0,
                )
            ),
            0.0,
        )

        node.avoidance_time_horizon = max(
            float(
                state.get(
                    "avoidance_time_horizon",
                    0.75,
                )
            ),
            0.0,
        )

        node.avoidance_strength = max(
            float(
                state.get(
                    "avoidance_strength",
                    1.0,
                )
            ),
            0.0,
        )

        target = state.get(
            "target_position"
        )

        if target is not None:
            node.set_target_position(
                float(
                    target[0]
                ),
                float(
                    target[1]
                ),
            )

    registry.register(
        "NavigationAgent2D",
        NavigationAgent2D,
        dump_state=dump_navigation_agent,
        load_state=load_navigation_agent,
    )

    # ==========================================================
    # NavigationObstacle2D
    # ==========================================================

    def dump_navigation_obstacle(
        node: NavigationObstacle2D,
    ) -> dict[str, Any]:
        return {
            "map_node_name": (
                node.map_node_name
            ),
            "radius_tiles": int(
                node.radius_tiles
            ),
            "blocking_enabled": bool(
                node.blocking_enabled
            ),
        }

    def load_navigation_obstacle(
        node: NavigationObstacle2D,
        state: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        del context

        map_name = state.get(
            "map_node_name"
        )

        node.map_node_name = (
            None
            if map_name is None
            else str(map_name)
        )

        node.radius_tiles = max(
            int(
                state.get(
                    "radius_tiles",
                    0,
                )
            ),
            0,
        )

        node.blocking_enabled = bool(
            state.get(
                "blocking_enabled",
                True,
            )
        )

    registry.register(
        "NavigationObstacle2D",
        NavigationObstacle2D,
        dump_state=dump_navigation_obstacle,
        load_state=load_navigation_obstacle,
    )

