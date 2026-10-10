from __future__ import annotations

from typing import Any

from nexora.nodes.effects import Light2D, LightOccluder2D, ParticleEmitter2D
from nexora.rendering.particles import ParticleConfig


def register_effect_nodes(registry) -> None:
    # ==========================================================
    # ParticleEmitter2D
    # ==========================================================

    def dump_particle_emitter(
        node: ParticleEmitter2D,
    ) -> dict[str, Any]:
        return {
            "config": (
                node.config.to_state()
            ),
            "emitting": bool(
                node.emitting
            ),
        }

    def load_particle_emitter(
        node: ParticleEmitter2D,
        state: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        del context

        node.config = (
            ParticleConfig.from_state(
                dict(
                    state.get(
                        "config",
                        {},
                    )
                )
            )
        )

        node.emitting = bool(
            state.get(
                "emitting",
                False,
            )
        )

    registry.register(
        "ParticleEmitter2D",
        ParticleEmitter2D,
        dump_state=dump_particle_emitter,
        load_state=load_particle_emitter,
    )

    # ==========================================================
    # Light2D
    # ==========================================================

    def dump_light_2d(
        node: Light2D,
    ) -> dict[str, Any]:
        return {
            "color": list(
                node.color
            ),
            "radius": float(
                node.radius
            ),
            "intensity": float(
                node.intensity
            ),
            "falloff": float(
                node.falloff
            ),
            "light_enabled": bool(
                node.light_enabled
            ),
            "light_mask": int(
                node.light_mask
            ),
            "cast_shadows": bool(
                node.cast_shadows
            ),
            "shadow_strength": float(
                node.shadow_strength
            ),
            "shadow_softness": float(
                node.shadow_softness
            ),
            "shadow_color": list(
                node.shadow_color
            ),
            "shadow_mask": int(
                node.shadow_mask
            ),
            "flicker_enabled": bool(
                node.flicker_enabled
            ),
            "flicker_strength": float(
                node.flicker_strength
            ),
            "flicker_speed": float(
                node.flicker_speed
            ),
            "pulse_enabled": bool(
                node.pulse_enabled
            ),
            "pulse_amount": float(
                node.pulse_amount
            ),
            "pulse_speed": float(
                node.pulse_speed
            ),
            "debug_draw": bool(
                node.debug_draw
            ),
            "debug_layer": int(
                node.debug_layer
            ),
        }

    def load_light_2d(
        node: Light2D,
        state: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        del context

        color = state.get(
            "color",
            (
                1.0,
                0.85,
                0.60,
            ),
        )

        node.color = tuple(
            float(value)
            for value
            in color[:3]
        )

        node.radius = float(
            state.get(
                "radius",
                180.0,
            )
        )

        node.intensity = float(
            state.get(
                "intensity",
                1.0,
            )
        )

        node.falloff = float(
            state.get(
                "falloff",
                2.0,
            )
        )

        node.light_enabled = bool(
            state.get(
                "light_enabled",
                True,
            )
        )

        node.light_mask = int(
            state.get(
                "light_mask",
                0xFFFFFFFF,
            )
        )

        node.cast_shadows = bool(
            state.get(
                "cast_shadows",
                False,
            )
        )

        node.shadow_strength = float(
            state.get(
                "shadow_strength",
                1.0,
            )
        )

        node.shadow_softness = float(
            state.get(
                "shadow_softness",
                0.0,
            )
        )

        shadow_color = state.get(
            "shadow_color",
            (
                0.0,
                0.0,
                0.0,
            ),
        )

        node.shadow_color = tuple(
            float(value)
            for value
            in shadow_color[:3]
        )

        node.shadow_mask = int(
            state.get(
                "shadow_mask",
                0xFFFFFFFF,
            )
        )

        node.flicker_enabled = bool(
            state.get(
                "flicker_enabled",
                False,
            )
        )

        node.flicker_strength = float(
            state.get(
                "flicker_strength",
                0.12,
            )
        )

        node.flicker_speed = float(
            state.get(
                "flicker_speed",
                17.0,
            )
        )

        node.pulse_enabled = bool(
            state.get(
                "pulse_enabled",
                False,
            )
        )

        node.pulse_amount = float(
            state.get(
                "pulse_amount",
                0.15,
            )
        )

        node.pulse_speed = float(
            state.get(
                "pulse_speed",
                2.0,
            )
        )

        node.debug_draw = bool(
            state.get(
                "debug_draw",
                False,
            )
        )

        node.debug_layer = int(
            state.get(
                "debug_layer",
                100_000,
            )
        )

    registry.register(
        "Light2D",
        Light2D,
        dump_state=dump_light_2d,
        load_state=load_light_2d,
    )

    # ==========================================================
    # LightOccluder2D
    # ==========================================================

    def dump_light_occluder_2d(
        node: LightOccluder2D,
    ) -> dict[str, Any]:
        return {
            "points": [
                list(point)
                for point
                in node.points
            ],
            "closed": bool(
                node.closed
            ),
            "occluder_enabled": bool(
                node.occluder_enabled
            ),
            "occluder_mask": int(
                node.occluder_mask
            ),
            "debug_draw": bool(
                node.debug_draw
            ),
            "debug_layer": int(
                node.debug_layer
            ),
        }

    def load_light_occluder_2d(
        node: LightOccluder2D,
        state: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        del context

        points = state.get(
            "points",
            (
                (
                    -32.0,
                    -32.0,
                ),
                (
                    32.0,
                    -32.0,
                ),
                (
                    32.0,
                    32.0,
                ),
                (
                    -32.0,
                    32.0,
                ),
            ),
        )

        node.set_polygon(
            points
        )

        node.closed = bool(
            state.get(
                "closed",
                True,
            )
        )

        node.occluder_enabled = bool(
            state.get(
                "occluder_enabled",
                True,
            )
        )

        node.occluder_mask = int(
            state.get(
                "occluder_mask",
                0xFFFFFFFF,
            )
        )

        node.debug_draw = bool(
            state.get(
                "debug_draw",
                False,
            )
        )

        node.debug_layer = int(
            state.get(
                "debug_layer",
                100_010,
            )
        )

    registry.register(
        "LightOccluder2D",
        LightOccluder2D,
        dump_state=dump_light_occluder_2d,
        load_state=load_light_occluder_2d,
    )

