from __future__ import annotations

from collections import defaultdict

from .property import InspectorProperty


class InspectorRegistry:
    """Property metadata registry used by the Nexora editor inspector."""

    def __init__(self) -> None:
        self._by_type: dict[type, list[InspectorProperty]] = defaultdict(list)

    def register(
        self,
        node_type: type,
        *properties: InspectorProperty,
    ) -> None:
        items = self._by_type[node_type]
        known = {item.key for item in items}

        for item in properties:
            if item.key in known:
                continue

            items.append(item)
            known.add(item.key)

    def properties_for(self, node) -> tuple[InspectorProperty, ...]:
        result: list[InspectorProperty] = []
        seen: set[str] = set()

        # Generic properties first, subclass-specific properties after.
        for node_type in reversed(type(node).__mro__):
            for prop in self._by_type.get(node_type, ()):
                if prop.key in seen:
                    continue

                result.append(prop)
                seen.add(prop.key)

        return tuple(result)

    def registered_properties(
        self,
    ) -> tuple[InspectorProperty, ...]:
        """Return all registered properties in stable registration order."""

        result: list[InspectorProperty] = []
        seen: set[str] = set()

        for properties in self._by_type.values():
            for prop in properties:
                if prop.key in seen:
                    continue

                result.append(prop)
                seen.add(prop.key)

        return tuple(result)


def create_default_inspector_registry(node_type: type) -> InspectorRegistry:
    """Create Nexora's built-in Inspector property registry.

    Imports are intentionally local so importing the inspector metadata module
    does not eagerly import every gameplay/render node during normal CLI use.
    """

    from nexora.animation import AnimationPlayer
    from nexora.nodes.camera.camera_2d import Camera2D
    from nexora.nodes.effects import (
        Light2D,
        LightOccluder2D,
        ParticleEmitter2D,
    )
    from nexora.nodes.entity.area_2d import Area2D
    from nexora.nodes.entity.body_2d import Body2D
    from nexora.nodes.entity.character_body_2d import CharacterBody2D
    from nexora.nodes.entity.character_controller_2d import CharacterController2D
    from nexora.nodes.entity.collision_shape_2d import CollisionShape2D
    from nexora.nodes.entity.ray_cast_2d import RayCast2D
    from nexora.nodes.navigation.navigation_agent_2d import NavigationAgent2D
    from nexora.nodes.navigation.navigation_obstacle_2d import NavigationObstacle2D
    from nexora.nodes.texture.animated_sprite import AnimatedSprite
    from nexora.nodes.world.tilemap_node import TileMapNode

    registry = InspectorRegistry()

    # ------------------------------------------------------------------
    # Base Node
    # ------------------------------------------------------------------

    registry.register(
        node_type,
        InspectorProperty(
            "name",
            "Name",
            "name",
            kind="text",
            group="Node",
        ),
        InspectorProperty(
            "enabled",
            "Enabled",
            "enabled",
            kind="bool",
            group="Node",
        ),
        InspectorProperty(
            "visible",
            "Visible",
            "visible",
            kind="bool",
            group="Node",
        ),
        InspectorProperty(
            "position_x",
            "Position X",
            "transform.x",
            kind="float",
            group="Transform",
            decimals=3,
        ),
        InspectorProperty(
            "position_y",
            "Position Y",
            "transform.y",
            kind="float",
            group="Transform",
            decimals=3,
        ),
        InspectorProperty(
            "rotation",
            "Rotation",
            "transform.rotation",
            kind="float",
            group="Transform",
            decimals=3,
        ),
        InspectorProperty(
            "scale_x",
            "Scale X",
            "transform.scale_x",
            kind="float",
            group="Transform",
            decimals=3,
        ),
        InspectorProperty(
            "scale_y",
            "Scale Y",
            "transform.scale_y",
            kind="float",
            group="Transform",
            decimals=3,
        ),
    )

    # ------------------------------------------------------------------
    # Sprite
    # ------------------------------------------------------------------

    registry.register(
        AnimatedSprite,
        InspectorProperty("sprite_width", "Width", "width", kind="float", group="Sprite", decimals=2),
        InspectorProperty("sprite_height", "Height", "height", kind="float", group="Sprite", decimals=2),
        InspectorProperty("sprite_alpha", "Alpha", "alpha", kind="float", group="Sprite", decimals=3),
        InspectorProperty("sprite_flip_x", "Flip X", "flip_x", kind="bool", group="Sprite"),
        InspectorProperty("sprite_flip_y", "Flip Y", "flip_y", kind="bool", group="Sprite"),
    )

    # ------------------------------------------------------------------
    # TileMap
    # ------------------------------------------------------------------

    registry.register(
        TileMapNode,
        InspectorProperty(
            "tilemap_asset",
            "TileMap Asset",
            "tilemap_asset",
            kind="text",
            group="TileMap",
            editable=False,
        ),
    )

    # ------------------------------------------------------------------
    # Physics bodies
    # ------------------------------------------------------------------

    registry.register(
        Body2D,
        InspectorProperty(
            "collision_layer",
            "Collision Layer",
            "collision_layer",
            kind="int",
            group="Physics",
        ),
        InspectorProperty(
            "collision_mask",
            "Collision Mask",
            "collision_mask",
            kind="int",
            group="Physics",
        ),
        InspectorProperty(
            "collision_enabled",
            "Collision Enabled",
            "collision_enabled",
            kind="bool",
            group="Physics",
        ),
    )

    registry.register(
        CharacterBody2D,
        InspectorProperty(
            "velocity_x",
            "Velocity X",
            "velocity.x",
            kind="float",
            group="Motion",
            decimals=3,
        ),
        InspectorProperty(
            "velocity_y",
            "Velocity Y",
            "velocity.y",
            kind="float",
            group="Motion",
            decimals=3,
        ),
    )

    registry.register(
        CharacterController2D,
        InspectorProperty("walk_speed", "Walk Speed", "walk_speed", kind="float", group="Controller", decimals=2),
        InspectorProperty("run_speed", "Run Speed", "run_speed", kind="float", group="Controller", decimals=2),
        InspectorProperty("acceleration", "Acceleration", "acceleration", kind="float", group="Controller", decimals=2),
        InspectorProperty("friction", "Friction", "friction", kind="float", group="Controller", decimals=2),
        InspectorProperty("roll_speed", "Roll Speed", "roll_speed", kind="float", group="Controller", decimals=2),
        InspectorProperty("roll_duration", "Roll Duration", "roll_duration", kind="float", group="Controller", decimals=3),
        InspectorProperty("max_health", "Max Health", "max_health", kind="float", group="Combat", decimals=1),
        InspectorProperty("health", "Health", "health", kind="float", group="Combat", decimals=1),
        InspectorProperty("floor_type", "Floor Type", "floor_type", kind="text", group="Audio"),
    )

    registry.register(
        Area2D,
        InspectorProperty(
            "monitoring",
            "Monitoring",
            "monitoring",
            kind="bool",
            group="Area",
        ),
        InspectorProperty(
            "monitorable",
            "Monitorable",
            "monitorable",
            kind="bool",
            group="Area",
        ),
    )

    registry.register(
        CollisionShape2D,
        InspectorProperty(
            "shape_width",
            "Width",
            "width",
            kind="float",
            group="Shape",
            decimals=3,
        ),
        InspectorProperty(
            "shape_height",
            "Height",
            "height",
            kind="float",
            group="Shape",
            decimals=3,
        ),
        InspectorProperty(
            "shape_disabled",
            "Disabled",
            "disabled",
            kind="bool",
            group="Shape",
        ),
    )

    registry.register(
        RayCast2D,
        InspectorProperty(
            "ray_target_x",
            "Target X",
            "target_x",
            kind="float",
            group="RayCast",
            decimals=3,
        ),
        InspectorProperty(
            "ray_target_y",
            "Target Y",
            "target_y",
            kind="float",
            group="RayCast",
            decimals=3,
        ),
        InspectorProperty(
            "ray_collision_mask",
            "Collision Mask",
            "collision_mask",
            kind="int",
            group="RayCast",
        ),
        InspectorProperty(
            "ray_bodies",
            "Collide Bodies",
            "collide_with_bodies",
            kind="bool",
            group="RayCast",
        ),
        InspectorProperty(
            "ray_areas",
            "Collide Areas",
            "collide_with_areas",
            kind="bool",
            group="RayCast",
        ),
        InspectorProperty(
            "ray_exclude_parent",
            "Exclude Parent",
            "exclude_parent_body",
            kind="bool",
            group="RayCast",
        ),
        InspectorProperty(
            "ray_enabled",
            "Ray Enabled",
            "raycast_enabled",
            kind="bool",
            group="RayCast",
        ),
    )

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Camera
    # ------------------------------------------------------------------

    registry.register(
        Camera2D,
        InspectorProperty(
            "camera_active",
            "Active",
            "active",
            kind="bool",
            group="Camera",
        ),
        InspectorProperty(
            "camera_zoom",
            "Zoom",
            "zoom",
            kind="float",
            group="Camera",
            decimals=3,
        ),
        InspectorProperty(
            "camera_clamp",
            "Clamp Bounds",
            "clamp_to_bounds",
            kind="bool",
            group="Camera",
        ),
        InspectorProperty(
            "camera_trauma",
            "Trauma",
            "trauma",
            kind="float",
            group="Camera Effects",
            decimals=3,
        ),
        InspectorProperty(
            "camera_trauma_decay",
            "Trauma Decay",
            "trauma_decay",
            kind="float",
            group="Camera Effects",
            decimals=3,
        ),
        InspectorProperty(
            "camera_trauma_strength",
            "Trauma Strength",
            "trauma_strength",
            kind="float",
            group="Camera Effects",
            decimals=3,
        ),
        InspectorProperty(
            "camera_trauma_power",
            "Trauma Power",
            "trauma_power",
            kind="float",
            group="Camera Effects",
            decimals=3,
        ),
        InspectorProperty(
            "camera_fade_alpha",
            "Fade Alpha",
            "fade_alpha",
            kind="float",
            group="Camera Effects",
            decimals=3,
        ),
        InspectorProperty(
            "camera_flash_alpha",
            "Flash Alpha",
            "flash_alpha",
            kind="float",
            group="Camera Effects",
            decimals=3,
        ),
        InspectorProperty(
            "camera_letterbox",
            "Letterbox",
            "letterbox_size",
            kind="float",
            group="Camera Effects",
            decimals=3,
        ),
    )

    # ------------------------------------------------------------------
    # Lighting
    # ------------------------------------------------------------------

    registry.register(
        Light2D,
        InspectorProperty(
            "light_enabled",
            "Light Enabled",
            "light_enabled",
            kind="bool",
            group="Light",
        ),
        InspectorProperty(
            "light_radius",
            "Radius",
            "radius",
            kind="float",
            group="Light",
            decimals=3,
        ),
        InspectorProperty(
            "light_intensity",
            "Intensity",
            "intensity",
            kind="float",
            group="Light",
            decimals=3,
        ),
        InspectorProperty(
            "light_falloff",
            "Falloff",
            "falloff",
            kind="float",
            group="Light",
            decimals=3,
        ),
        InspectorProperty(
            "light_mask",
            "Light Mask",
            "light_mask",
            kind="int",
            group="Light",
        ),
        InspectorProperty(
            "light_cast_shadows",
            "Cast Shadows",
            "cast_shadows",
            kind="bool",
            group="Shadows",
        ),
        InspectorProperty(
            "light_shadow_strength",
            "Strength",
            "shadow_strength",
            kind="float",
            group="Shadows",
            decimals=3,
        ),
        InspectorProperty(
            "light_shadow_softness",
            "Softness",
            "shadow_softness",
            kind="float",
            group="Shadows",
            decimals=3,
        ),
        InspectorProperty(
            "light_shadow_mask",
            "Shadow Mask",
            "shadow_mask",
            kind="int",
            group="Shadows",
        ),
        InspectorProperty(
            "light_flicker_enabled",
            "Flicker",
            "flicker_enabled",
            kind="bool",
            group="Flicker",
        ),
        InspectorProperty(
            "light_flicker_strength",
            "Strength",
            "flicker_strength",
            kind="float",
            group="Flicker",
            decimals=3,
        ),
        InspectorProperty(
            "light_flicker_speed",
            "Speed",
            "flicker_speed",
            kind="float",
            group="Flicker",
            decimals=3,
        ),
        InspectorProperty(
            "light_pulse_enabled",
            "Pulse",
            "pulse_enabled",
            kind="bool",
            group="Pulse",
        ),
        InspectorProperty(
            "light_pulse_amount",
            "Amount",
            "pulse_amount",
            kind="float",
            group="Pulse",
            decimals=3,
        ),
        InspectorProperty(
            "light_pulse_speed",
            "Speed",
            "pulse_speed",
            kind="float",
            group="Pulse",
            decimals=3,
        ),
        InspectorProperty(
            "light_debug_draw",
            "Debug Draw",
            "debug_draw",
            kind="bool",
            group="Debug",
        ),
        InspectorProperty(
            "light_debug_layer",
            "Debug Layer",
            "debug_layer",
            kind="int",
            group="Debug",
        ),
    )

    registry.register(
        LightOccluder2D,
        InspectorProperty(
            "occluder_closed",
            "Closed",
            "closed",
            kind="bool",
            group="Occluder",
        ),
        InspectorProperty(
            "occluder_enabled",
            "Enabled",
            "occluder_enabled",
            kind="bool",
            group="Occluder",
        ),
        InspectorProperty(
            "occluder_mask",
            "Mask",
            "occluder_mask",
            kind="int",
            group="Occluder",
        ),
        InspectorProperty(
            "occluder_debug_draw",
            "Debug Draw",
            "debug_draw",
            kind="bool",
            group="Debug",
        ),
        InspectorProperty(
            "occluder_debug_layer",
            "Debug Layer",
            "debug_layer",
            kind="int",
            group="Debug",
        ),
    )

    # ------------------------------------------------------------------
    # Animation / particles
    # ------------------------------------------------------------------

    registry.register(
        AnimationPlayer,
        InspectorProperty(
            "animation_speed_scale",
            "Speed Scale",
            "speed_scale",
            kind="float",
            group="Animation",
            decimals=3,
        ),
        InspectorProperty(
            "animation_autoplay",
            "Autoplay",
            "autoplay",
            kind="text",
            group="Animation",
        ),
        InspectorProperty(
            "animation_target",
            "Target Node",
            "target_node_name",
            kind="text",
            group="Animation",
        ),
    )

    registry.register(
        ParticleEmitter2D,
        InspectorProperty(
            "particle_emitting",
            "Emitting",
            "emitting",
            kind="bool",
            group="Particles",
        ),
    )

    return registry
