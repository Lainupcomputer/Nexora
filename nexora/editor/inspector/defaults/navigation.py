from __future__ import annotations

from ..property import InspectorProperty
from nexora.nodes.navigation.navigation_agent_2d import NavigationAgent2D
from nexora.nodes.navigation.navigation_obstacle_2d import NavigationObstacle2D

def register_navigation_defaults(registry) -> None:
    registry.register(
            NavigationAgent2D,
            InspectorProperty(
                "nav_map_node",
                "Map Node",
                "map_node_name",
                kind="text",
                group="Navigation",
            ),
            InspectorProperty(
                "nav_layer",
                "Layer",
                "layer_name",
                kind="text",
                group="Navigation",
            ),
            InspectorProperty(
                "nav_diagonal",
                "Allow Diagonal",
                "allow_diagonal",
                kind="bool",
                group="Navigation",
            ),
            InspectorProperty(
                "nav_corner_cutting",
                "Corner Cutting",
                "allow_corner_cutting",
                kind="bool",
                group="Navigation",
            ),
            InspectorProperty(
                "nav_empty_walkable",
                "Empty Walkable",
                "empty_walkable",
                kind="bool",
                group="Navigation",
            ),
            InspectorProperty(
                "nav_default_cost",
                "Default Cost",
                "default_cost",
                kind="float",
                group="Navigation",
                decimals=3,
            ),
            InspectorProperty(
                "nav_cache_paths",
                "Cache Paths",
                "cache_paths",
                kind="bool",
                group="Navigation",
            ),
            InspectorProperty(
                "nav_waypoint_tolerance",
                "Waypoint Tolerance",
                "waypoint_tolerance",
                kind="float",
                group="Navigation",
                decimals=3,
            ),
            InspectorProperty(
                "nav_target_tolerance",
                "Target Tolerance",
                "target_tolerance",
                kind="float",
                group="Navigation",
                decimals=3,
            ),
            InspectorProperty(
                "nav_auto_repath",
                "Auto Repath",
                "auto_repath",
                kind="bool",
                group="Repath",
            ),
            InspectorProperty(
                "nav_repath_interval",
                "Repath Interval",
                "repath_interval",
                kind="float",
                group="Repath",
                decimals=3,
            ),
            InspectorProperty(
                "nav_avoidance_enabled",
                "Avoidance",
                "avoidance_enabled",
                kind="bool",
                group="Avoidance",
            ),
            InspectorProperty(
                "nav_avoidance_radius",
                "Radius",
                "avoidance_radius",
                kind="float",
                group="Avoidance",
                decimals=3,
            ),
            InspectorProperty(
                "nav_neighbor_distance",
                "Neighbor Distance",
                "avoidance_neighbor_distance",
                kind="float",
                group="Avoidance",
                decimals=3,
            ),
            InspectorProperty(
                "nav_time_horizon",
                "Time Horizon",
                "avoidance_time_horizon",
                kind="float",
                group="Avoidance",
                decimals=3,
            ),
            InspectorProperty(
                "nav_avoidance_strength",
                "Strength",
                "avoidance_strength",
                kind="float",
                group="Avoidance",
                decimals=3,
            ),
        )

    registry.register(
            NavigationObstacle2D,
            InspectorProperty(
                "obstacle_map_node",
                "Map Node",
                "map_node_name",
                kind="text",
                group="Obstacle",
            ),
            InspectorProperty(
                "obstacle_radius_tiles",
                "Radius Tiles",
                "radius_tiles",
                kind="int",
                group="Obstacle",
            ),
            InspectorProperty(
                "obstacle_blocking",
                "Blocking",
                "blocking_enabled",
                kind="bool",
                group="Obstacle",
            ),
        )
