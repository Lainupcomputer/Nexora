from __future__ import annotations

from ..property import InspectorProperty
from nexora.animation import AnimationPlayer
from nexora.nodes.effects import ParticleEmitter2D

def register_animation_defaults(registry) -> None:
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
