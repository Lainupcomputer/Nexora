from __future__ import annotations

from typing import Any

from nexora.nodes.physics.area_2d import Area2D
from nexora.nodes.physics.body_2d import Body2D
from nexora.nodes.physics.character_body_2d import CharacterBody2D
from nexora.nodes.physics.character_controller_2d import CharacterController2D
from nexora.nodes.physics.collision_shape_2d import CollisionShape2D
from nexora.nodes.physics.ray_cast_2d import RayCast2D
from nexora.nodes.physics.static_body_2d import StaticBody2D


def register_physics_nodes(registry) -> None:
    # ==========================================================
    # Physics body
    # ==========================================================

    def dump_body(
        node: Body2D,
    ) -> dict[str, Any]:
        return {
            "collision_layer": int(
                node.collision_layer
            ),
            "collision_mask": int(
                node.collision_mask
            ),
            "collision_enabled": bool(
                node.collision_enabled
            ),
        }

    def load_body(
        node: Body2D,
        state: dict[str, Any],
        context,
    ) -> None:
        node.collision_layer = int(
            state.get(
                "collision_layer",
                1,
            )
        )

        node.collision_mask = int(
            state.get(
                "collision_mask",
                0xFFFFFFFF,
            )
        )

        node.collision_enabled = bool(
            state.get(
                "collision_enabled",
                True,
            )
        )

    registry.register(
        "Body2D",
        Body2D,
        dump_state=dump_body,
        load_state=load_body,
    )

    registry.register(
        "StaticBody2D",
        StaticBody2D,
        dump_state=dump_body,
        load_state=load_body,
    )

    # ==========================================================
    # Area2D
    # ==========================================================

    def dump_area(
        node: Area2D,
    ) -> dict[str, Any]:
        data = dump_body(
            node
        )

        data.update(
            {
                "monitoring": bool(
                    node.monitoring
                ),
                "monitorable": bool(
                    node.monitorable
                ),
            }
        )

        return data

    def load_area(
        node: Area2D,
        state: dict[str, Any],
        context,
    ) -> None:
        load_body(
            node,
            state,
            context,
        )

        node.monitoring = bool(
            state.get(
                "monitoring",
                True,
            )
        )

        node.monitorable = bool(
            state.get(
                "monitorable",
                True,
            )
        )

    registry.register(
        "Area2D",
        Area2D,
        dump_state=dump_area,
        load_state=load_area,
    )

    # ==========================================================
    # CharacterBody2D
    # ==========================================================

    def dump_character(
        node: CharacterBody2D,
    ) -> dict[str, Any]:
        data = dump_body(
            node
        )

        data[
            "velocity"
        ] = (
            float(
                node.velocity.x
            ),
            float(
                node.velocity.y
            ),
        )

        return data

    def load_character(
        node: CharacterBody2D,
        state: dict[str, Any],
        context,
    ) -> None:
        load_body(
            node,
            state,
            context,
        )

        velocity = state.get(
            "velocity",
            (
                0.0,
                0.0,
            ),
        )

        node.velocity.set(
            float(
                velocity[0]
            ),
            float(
                velocity[1]
            ),
        )

    registry.register(
        "CharacterBody2D",
        CharacterBody2D,
        dump_state=dump_character,
        load_state=load_character,
    )

    # ==========================================================
    # CharacterController2D
    # ==========================================================

    def dump_character_controller(
        node: CharacterController2D,
    ) -> dict[str, Any]:
        data = dump_character(node)
        data.update(
            {
                "walk_speed": float(node.walk_speed),
                "run_speed": float(node.run_speed),
                "acceleration": float(node.acceleration),
                "friction": float(node.friction),
                "roll_speed": float(node.roll_speed),
                "roll_duration": float(node.roll_duration),
                "roll_cooldown": float(node.roll_cooldown),
                "max_health": float(node.max_health),
                "health": float(node.health),
                "floor_type": str(node.floor_type),
                "footstep_interval_walk": float(node.footstep_interval_walk),
                "footstep_interval_run": float(node.footstep_interval_run),
                "input_actions": dict(node.input_actions),
                "active_weapon": node.active_weapon,
                "active_tool": node.active_tool,
                "weapon_profiles": {
                    name: {
                        "animation": profile.animation,
                        "duration": float(profile.duration),
                        "damage": float(profile.damage),
                    }
                    for name, profile in node.weapon_profiles.items()
                },
                "tool_profiles": {
                    name: {
                        "animation": profile.animation,
                        "duration": float(profile.duration),
                        "damage": float(profile.damage),
                    }
                    for name, profile in node.tool_profiles.items()
                },
            }
        )
        return data

    def load_character_controller(
        node: CharacterController2D,
        state: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        load_character(node, state, context)
        for attribute in (
            "walk_speed", "run_speed", "acceleration", "friction",
            "roll_speed", "roll_duration", "roll_cooldown", "max_health",
            "health", "footstep_interval_walk", "footstep_interval_run",
        ):
            if attribute in state:
                setattr(node, attribute, float(state[attribute]))
        node.floor_type = str(state.get("floor_type", node.floor_type))
        actions = state.get("input_actions")
        if isinstance(actions, dict):
            node.input_actions.update({str(key): str(value) for key, value in actions.items()})
        for key, profile in state.get("weapon_profiles", {}).items():
            if isinstance(profile, dict):
                node.register_weapon(str(key), profile)
        for key, profile in state.get("tool_profiles", {}).items():
            if isinstance(profile, dict):
                node.register_tool(str(key), profile)
        node.active_weapon = state.get("active_weapon")
        node.active_tool = state.get("active_tool")

    registry.register(
        "CharacterController2D",
        CharacterController2D,
        dump_state=dump_character_controller,
        load_state=load_character_controller,
    )

    # ==========================================================
    # CollisionShape2D
    # ==========================================================

    def dump_shape(
        node: CollisionShape2D,
    ) -> dict[str, Any]:
        return {
            "width": float(
                node.width
            ),
            "height": float(
                node.height
            ),
            "disabled": bool(
                node.disabled
            ),
        }

    def load_shape(
        node: CollisionShape2D,
        state: dict[str, Any],
        context,
    ) -> None:
        node.set_size(
            float(
                state.get(
                    "width",
                    32.0,
                )
            ),
            float(
                state.get(
                    "height",
                    32.0,
                )
            ),
        )

        node.disabled = bool(
            state.get(
                "disabled",
                False,
            )
        )

    registry.register(
        "CollisionShape2D",
        CollisionShape2D,
        dump_state=dump_shape,
        load_state=load_shape,
    )

    # ==========================================================
    # RayCast2D
    # ==========================================================

    def dump_ray(
        node: RayCast2D,
    ) -> dict[str, Any]:
        return {
            "target_x": float(
                node.target_x
            ),
            "target_y": float(
                node.target_y
            ),
            "collision_mask": int(
                node.collision_mask
            ),
            "collide_with_bodies": bool(
                node.collide_with_bodies
            ),
            "collide_with_areas": bool(
                node.collide_with_areas
            ),
            "exclude_parent_body": bool(
                node.exclude_parent_body
            ),
            "raycast_enabled": bool(
                node.raycast_enabled
            ),
        }

    def load_ray(
        node: RayCast2D,
        state: dict[str, Any],
        context,
    ) -> None:
        node.target_x = float(
            state.get(
                "target_x",
                64.0,
            )
        )

        node.target_y = float(
            state.get(
                "target_y",
                0.0,
            )
        )

        node.collision_mask = int(
            state.get(
                "collision_mask",
                0xFFFFFFFF,
            )
        )

        node.collide_with_bodies = bool(
            state.get(
                "collide_with_bodies",
                True,
            )
        )

        node.collide_with_areas = bool(
            state.get(
                "collide_with_areas",
                True,
            )
        )

        node.exclude_parent_body = bool(
            state.get(
                "exclude_parent_body",
                True,
            )
        )

        node.raycast_enabled = bool(
            state.get(
                "raycast_enabled",
                True,
            )
        )

    registry.register(
        "RayCast2D",
        RayCast2D,
        dump_state=dump_ray,
        load_state=load_ray,
    )

