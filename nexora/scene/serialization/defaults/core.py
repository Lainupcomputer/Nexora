from __future__ import annotations

from typing import Any

from nexora.animation import AnimationClip, AnimationEvent, AnimationFrame, AnimationPlayer
from nexora.nodes.node import Node
from nexora.nodes.texture.animated_sprite import AnimatedSprite


def register_core_nodes(registry) -> None:
    def dump_animations(node) -> list[dict[str, Any]]:
        return [
            {
                "name": clip.name,
                "loop": bool(clip.loop),
                "frames": [
                    {
                        "index": int(frame.index),
                        "duration": float(frame.duration),
                        "uv": frame.uv,
                    }
                    for frame in clip.frames
                ],
                "events": [
                    {
                        "frame": int(event.frame),
                        "name": event.name,
                        "data": event.data,
                    }
                    for event in clip.events
                ],
            }
            for clip in node.animations
        ]

    def load_animations(node, state: dict[str, Any]) -> None:
        for clip_state in state.get("animations", []):
            frames = tuple(
                AnimationFrame(
                    index=int(frame["index"]),
                    duration=float(frame["duration"]),
                    uv=(
                        None
                        if frame.get("uv") is None
                        else tuple(frame["uv"])
                    ),
                )
                for frame in clip_state.get("frames", [])
            )
            events = tuple(
                AnimationEvent(
                    frame=int(event["frame"]),
                    name=str(event["name"]),
                    data=event.get("data"),
                )
                for event in clip_state.get("events", [])
            )
            node.add_animation(
                AnimationClip(
                    name=str(clip_state["name"]),
                    frames=frames,
                    loop=bool(clip_state.get("loop", True)),
                    events=events,
                )
            )

    # ==========================================================
    # Base Node
    # ==========================================================

    registry.register(
        "Node",
        Node,
    )

    # ==========================================================
    # AnimatedSprite
    # ==========================================================

    def dump_animated_sprite(
        node: AnimatedSprite,
    ) -> dict[str, Any]:
        source = getattr(
            node,
            "_nexora_texture_source",
            None,
        )

        return {
            "texture_source": (
                None
                if source is None
                else str(source)
            ),
            "width": float(
                node.width
            ),
            "height": float(
                node.height
            ),
            "origin": (
                float(
                    node.origin[0]
                ),
                float(
                    node.origin[1]
                ),
            ),
            "alpha": float(
                node.alpha
            ),
            "flip_x": bool(
                node.flip_x
            ),
            "flip_y": bool(
                node.flip_y
            ),
            "uv": tuple(
                float(value)
                for value
                in node.uv
            ),
            "animations": dump_animations(node),
        }

    def load_animated_sprite(
        node: AnimatedSprite,
        state: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        node.width = float(
            state.get(
                "width",
                64.0,
            )
        )

        node.height = float(
            state.get(
                "height",
                64.0,
            )
        )

        origin = state.get(
            "origin",
            (
                0.5,
                0.5,
            ),
        )

        node.origin = (
            float(
                origin[0]
            ),
            float(
                origin[1]
            ),
        )

        node.alpha = float(
            state.get(
                "alpha",
                1.0,
            )
        )

        node.flip_x = bool(
            state.get(
                "flip_x",
                False,
            )
        )

        node.flip_y = bool(
            state.get(
                "flip_y",
                False,
            )
        )

        uv = state.get(
            "uv",
            (
                0.0,
                0.0,
                1.0,
                1.0,
            ),
        )

        node.uv = tuple(
            float(value)
            for value
            in uv
        )

        load_animations(node, state)

        source = state.get(
            "texture_source"
        )

        if not source:
            node.texture = None

            node._nexora_texture_source = (
                None
            )

            return

        source = str(
            source
        )

        node._nexora_texture_source = (
            source
        )

        assets = context.get(
            "assets"
        )

        if assets is None:
            node.texture = None
            return

        node.texture = (
            assets.texture(
                source
            )
        )

    registry.register(
        "AnimatedSprite",
        AnimatedSprite,
        dump_state=dump_animated_sprite,
        load_state=load_animated_sprite,
    )

    # ==========================================================
    # AnimationPlayer
    # ==========================================================

    def dump_animation_player(
        node: AnimationPlayer,
    ) -> dict[str, Any]:
        return {
            "speed_scale": float(
                node.speed_scale
            ),
            "autoplay": (
                node.autoplay
            ),
            "target_node_name": (
                node.target_node_name
            ),
            "animations": [
                {
                    "name": clip.name,
                    "loop": bool(
                        clip.loop
                    ),
                    "frames": [
                        {
                            "index": int(
                                frame.index
                            ),
                            "duration": float(
                                frame.duration
                            ),
                            "uv": frame.uv,
                        }
                        for frame
                        in clip.frames
                    ],
                    "events": [
                        {
                            "frame": int(
                                event.frame
                            ),
                            "name": (
                                event.name
                            ),
                            "data": (
                                event.data
                            ),
                        }
                        for event
                        in clip.events
                    ],
                }
                for clip
                in node.animations
            ],
        }

    def load_animation_player(
        node: AnimationPlayer,
        state: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        del context

        node.speed_scale = float(
            state.get(
                "speed_scale",
                1.0,
            )
        )

        autoplay = state.get(
            "autoplay"
        )

        node.autoplay = (
            None
            if autoplay is None
            else str(autoplay)
        )

        target = state.get(
            "target_node_name"
        )

        node.target_node_name = (
            None
            if target is None
            else str(target)
        )

        for clip_state in state.get(
            "animations",
            [],
        ):
            frames = tuple(
                AnimationFrame(
                    index=int(
                        frame[
                            "index"
                        ]
                    ),
                    duration=float(
                        frame[
                            "duration"
                        ]
                    ),
                    uv=(
                        None
                        if frame.get(
                            "uv"
                        ) is None
                        else tuple(
                            frame[
                                "uv"
                            ]
                        )
                    ),
                )
                for frame
                in clip_state.get(
                    "frames",
                    [],
                )
            )

            events = tuple(
                AnimationEvent(
                    frame=int(
                        event[
                            "frame"
                        ]
                    ),
                    name=str(
                        event[
                            "name"
                        ]
                    ),
                    data=event.get(
                        "data"
                    ),
                )
                for event
                in clip_state.get(
                    "events",
                    [],
                )
            )

            node.add_animation(
                AnimationClip(
                    name=str(
                        clip_state[
                            "name"
                        ]
                    ),
                    frames=frames,
                    loop=bool(
                        clip_state.get(
                            "loop",
                            True,
                        )
                    ),
                    events=events,
                )
            )

    registry.register(
        "AnimationPlayer",
        AnimationPlayer,
        dump_state=dump_animation_player,
        load_state=load_animation_player,
    )

