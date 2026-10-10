from __future__ import annotations

from ..property import InspectorProperty
from nexora.nodes.physics.area_2d import Area2D
from nexora.nodes.physics.body_2d import Body2D
from nexora.nodes.physics.character_body_2d import CharacterBody2D
from nexora.nodes.physics.character_controller_2d import CharacterController2D
from nexora.nodes.physics.collision_shape_2d import CollisionShape2D
from nexora.nodes.physics.ray_cast_2d import RayCast2D

def register_physics_defaults(registry) -> None:
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
