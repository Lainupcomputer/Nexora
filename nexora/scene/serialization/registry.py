from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from nexora.nodes.node import Node
from nexora.nodes.entity.body_2d import Body2D
from nexora.nodes.entity.static_body_2d import StaticBody2D
from nexora.nodes.entity.area_2d import Area2D
from nexora.nodes.entity.character_body_2d import CharacterBody2D
from nexora.nodes.entity.collision_shape_2d import CollisionShape2D
from nexora.nodes.entity.ray_cast_2d import RayCast2D
from nexora.nodes.world.tilemap_node import TileMapNode
from nexora.nodes.navigation.navigation_agent_2d import NavigationAgent2D
from nexora.nodes.navigation.navigation_obstacle_2d import NavigationObstacle2D
from nexora.tilemap import TileMap, TileSet
from nexora.animation import AnimationClip, AnimationEvent, AnimationFrame, AnimationPlayer
from nexora.nodes.effects import ParticleEmitter2D, Light2D, LightOccluder2D
from nexora.particles import ParticleConfig

from .errors import UnregisteredNodeTypeError


Factory = Callable[[str, Any, dict[str, Any]], Node]
DumpState = Callable[[Node], dict[str, Any]]
LoadState = Callable[[Node, dict[str, Any], dict[str, Any]], None]


@dataclass(slots=True)
class NodeAdapter:
    type_id: str
    node_type: type[Node]
    factory: Factory
    dump_state: DumpState
    load_state: LoadState


class NodeFactoryRegistry:
    """
    Safe node registry.

    Files contain only a string type id. Loading never imports a class from
    a path stored in the file. A type must already be registered here.
    """

    def __init__(self, *, register_defaults: bool = True) -> None:
        self._by_id: dict[str, NodeAdapter] = {}
        self._by_type: dict[type[Node], NodeAdapter] = {}
        if register_defaults:
            self._register_defaults()

    def register(
        self,
        type_id: str,
        node_type: type[Node],
        *,
        factory: Factory | None = None,
        dump_state: DumpState | None = None,
        load_state: LoadState | None = None,
    ) -> None:
        type_id = str(type_id).strip()
        if not type_id:
            raise ValueError("type_id cannot be empty")
        if not issubclass(node_type, Node):
            raise TypeError("node_type must inherit from Node")
        if type_id in self._by_id:
            raise ValueError(f"Node type id already registered: {type_id}")

        if factory is None:
            def factory(name, world, context, cls=node_type):
                return cls(name, world)

        if dump_state is None:
            dump_state = lambda node: {}

        if load_state is None:
            load_state = lambda node, state, context: None

        adapter = NodeAdapter(
            type_id=type_id,
            node_type=node_type,
            factory=factory,
            dump_state=dump_state,
            load_state=load_state,
        )
        self._by_id[type_id] = adapter
        self._by_type[node_type] = adapter

    def adapter_for_node(self, node: Node) -> NodeAdapter:
        adapter = self._by_type.get(type(node))
        if adapter is None:
            raise UnregisteredNodeTypeError(
                f"Node type is not registered: {type(node).__module__}."
                f"{type(node).__qualname__}"
            )
        return adapter

    def create(
        self,
        type_id: str,
        name: str,
        world,
        *,
        context: dict[str, Any] | None = None,
    ) -> Node:
        adapter = self._by_id.get(str(type_id))
        if adapter is None:
            raise UnregisteredNodeTypeError(
                f"Node type id is not registered: {type_id!r}"
            )
        return adapter.factory(str(name), world, context or {})

    def dump_properties(self, node: Node) -> dict[str, Any]:
        return dict(self.adapter_for_node(node).dump_state(node))

    def load_properties(
        self,
        node: Node,
        state: dict[str, Any],
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.adapter_for_node(node).load_state(
            node,
            dict(state),
            context or {},
        )

    def type_id_for(self, node: Node) -> str:
        return self.adapter_for_node(node).type_id

    def _register_defaults(self) -> None:
        self.register("Node", Node)

        def dump_body(node: Body2D) -> dict[str, Any]:
            return {
                "collision_layer": int(node.collision_layer),
                "collision_mask": int(node.collision_mask),
                "collision_enabled": bool(node.collision_enabled),
            }

        def load_body(node: Body2D, state: dict[str, Any], context) -> None:
            node.collision_layer = int(state.get("collision_layer", 1))
            node.collision_mask = int(state.get("collision_mask", 0xFFFFFFFF))
            node.collision_enabled = bool(state.get("collision_enabled", True))

        self.register(
            "Body2D",
            Body2D,
            dump_state=dump_body,
            load_state=load_body,
        )
        self.register(
            "StaticBody2D",
            StaticBody2D,
            dump_state=dump_body,
            load_state=load_body,
        )

        def dump_area(node: Area2D) -> dict[str, Any]:
            data = dump_body(node)
            data.update({
                "monitoring": bool(node.monitoring),
                "monitorable": bool(node.monitorable),
            })
            return data

        def load_area(node: Area2D, state: dict[str, Any], context) -> None:
            load_body(node, state, context)
            node.monitoring = bool(state.get("monitoring", True))
            node.monitorable = bool(state.get("monitorable", True))

        self.register(
            "Area2D",
            Area2D,
            dump_state=dump_area,
            load_state=load_area,
        )

        def dump_character(node: CharacterBody2D) -> dict[str, Any]:
            data = dump_body(node)
            data["velocity"] = (
                float(node.velocity.x),
                float(node.velocity.y),
            )
            return data

        def load_character(node: CharacterBody2D, state: dict[str, Any], context) -> None:
            load_body(node, state, context)
            velocity = state.get("velocity", (0.0, 0.0))
            node.velocity.set(float(velocity[0]), float(velocity[1]))

        self.register(
            "CharacterBody2D",
            CharacterBody2D,
            dump_state=dump_character,
            load_state=load_character,
        )

        def dump_shape(node: CollisionShape2D) -> dict[str, Any]:
            return {
                "width": float(node.width),
                "height": float(node.height),
                "disabled": bool(node.disabled),
            }

        def load_shape(node: CollisionShape2D, state: dict[str, Any], context) -> None:
            node.set_size(
                float(state.get("width", 32.0)),
                float(state.get("height", 32.0)),
            )
            node.disabled = bool(state.get("disabled", False))

        self.register(
            "CollisionShape2D",
            CollisionShape2D,
            dump_state=dump_shape,
            load_state=load_shape,
        )

        def dump_ray(node: RayCast2D) -> dict[str, Any]:
            return {
                "target_x": float(node.target_x),
                "target_y": float(node.target_y),
                "collision_mask": int(node.collision_mask),
                "collide_with_bodies": bool(node.collide_with_bodies),
                "collide_with_areas": bool(node.collide_with_areas),
                "exclude_parent_body": bool(node.exclude_parent_body),
                "raycast_enabled": bool(node.raycast_enabled),
            }

        def load_ray(node: RayCast2D, state: dict[str, Any], context) -> None:
            node.target_x = float(state.get("target_x", 64.0))
            node.target_y = float(state.get("target_y", 0.0))
            node.collision_mask = int(state.get("collision_mask", 0xFFFFFFFF))
            node.collide_with_bodies = bool(state.get("collide_with_bodies", True))
            node.collide_with_areas = bool(state.get("collide_with_areas", True))
            node.exclude_parent_body = bool(state.get("exclude_parent_body", True))
            node.raycast_enabled = bool(state.get("raycast_enabled", True))

        self.register(
            "RayCast2D",
            RayCast2D,
            dump_state=dump_ray,
            load_state=load_ray,
        )

        def dump_navigation_agent(node: NavigationAgent2D) -> dict[str, Any]:
            return {
                "map_node_name": node.map_node_name,
                "layer_name": str(node.layer_name),
                "allow_diagonal": bool(node.allow_diagonal),
                "allow_corner_cutting": bool(node.allow_corner_cutting),
                "empty_walkable": bool(node.empty_walkable),
                "default_cost": float(node.default_cost),
                "cache_paths": bool(node.cache_paths),
                "waypoint_tolerance": float(node.waypoint_tolerance),
                "target_tolerance": float(node.target_tolerance),
                "auto_repath": bool(node.auto_repath),
                "repath_interval": float(node.repath_interval),
                "avoidance_enabled": bool(node.avoidance_enabled),
                "avoidance_radius": float(node.avoidance_radius),
                "avoidance_neighbor_distance": float(node.avoidance_neighbor_distance),
                "avoidance_time_horizon": float(node.avoidance_time_horizon),
                "avoidance_strength": float(node.avoidance_strength),
                "target_position": node.target_position,
            }

        def load_navigation_agent(
            node: NavigationAgent2D,
            state: dict[str, Any],
            context: dict[str, Any],
        ) -> None:
            map_name = state.get("map_node_name")
            node.map_node_name = None if map_name is None else str(map_name)
            node.layer_name = str(state.get("layer_name", "ground"))
            node.allow_diagonal = bool(state.get("allow_diagonal", False))
            node.allow_corner_cutting = bool(
                state.get("allow_corner_cutting", False)
            )
            node.empty_walkable = bool(state.get("empty_walkable", True))
            node.default_cost = float(state.get("default_cost", 1.0))
            node.cache_paths = bool(state.get("cache_paths", True))
            node.waypoint_tolerance = float(state.get("waypoint_tolerance", 4.0))
            node.target_tolerance = float(state.get("target_tolerance", 4.0))
            node.auto_repath = bool(state.get("auto_repath", True))
            node.repath_interval = float(state.get("repath_interval", 0.25))
            node.avoidance_enabled = bool(state.get("avoidance_enabled", True))
            node.avoidance_radius = max(float(state.get("avoidance_radius", 12.0)), 0.0)
            node.avoidance_neighbor_distance = max(
                float(state.get("avoidance_neighbor_distance", 64.0)), 0.0
            )
            node.avoidance_time_horizon = max(
                float(state.get("avoidance_time_horizon", 0.75)), 0.0
            )
            node.avoidance_strength = max(
                float(state.get("avoidance_strength", 1.0)), 0.0
            )

            target = state.get("target_position")
            if target is not None:
                node.set_target_position(float(target[0]), float(target[1]))

        self.register(
            "NavigationAgent2D",
            NavigationAgent2D,
            dump_state=dump_navigation_agent,
            load_state=load_navigation_agent,
        )

        def dump_navigation_obstacle(
            node: NavigationObstacle2D,
        ) -> dict[str, Any]:
            return {
                "map_node_name": node.map_node_name,
                "radius_tiles": int(node.radius_tiles),
                "blocking_enabled": bool(node.blocking_enabled),
            }

        def load_navigation_obstacle(
            node: NavigationObstacle2D,
            state: dict[str, Any],
            context: dict[str, Any],
        ) -> None:
            del context
            map_name = state.get("map_node_name")
            node.map_node_name = None if map_name is None else str(map_name)
            node.radius_tiles = max(int(state.get("radius_tiles", 0)), 0)
            node.blocking_enabled = bool(state.get("blocking_enabled", True))

        self.register(
            "NavigationObstacle2D",
            NavigationObstacle2D,
            dump_state=dump_navigation_obstacle,
            load_state=load_navigation_obstacle,
        )


        def dump_animation_player(node: AnimationPlayer) -> dict[str, Any]:
            return {
                "speed_scale": float(node.speed_scale),
                "autoplay": node.autoplay,
                "target_node_name": node.target_node_name,
                "animations": [
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
                ],
            }

        def load_animation_player(
            node: AnimationPlayer,
            state: dict[str, Any],
            context: dict[str, Any],
        ) -> None:
            del context
            node.speed_scale = float(state.get("speed_scale", 1.0))
            autoplay = state.get("autoplay")
            node.autoplay = None if autoplay is None else str(autoplay)
            target = state.get("target_node_name")
            node.target_node_name = None if target is None else str(target)
            for clip_state in state.get("animations", []):
                frames = tuple(
                    AnimationFrame(
                        index=int(frame["index"]),
                        duration=float(frame["duration"]),
                        uv=None if frame.get("uv") is None else tuple(frame["uv"]),
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

        self.register(
            "AnimationPlayer",
            AnimationPlayer,
            dump_state=dump_animation_player,
            load_state=load_animation_player,
        )


        def dump_particle_emitter(node: ParticleEmitter2D) -> dict[str, Any]:
            return {
                "config": node.config.to_state(),
                "emitting": bool(node.emitting),
            }

        def load_particle_emitter(
            node: ParticleEmitter2D,
            state: dict[str, Any],
            context: dict[str, Any],
        ) -> None:
            del context
            node.config = ParticleConfig.from_state(dict(state.get("config", {})))
            node.emitting = bool(state.get("emitting", False))

        self.register(
            "ParticleEmitter2D",
            ParticleEmitter2D,
            dump_state=dump_particle_emitter,
            load_state=load_particle_emitter,
        )

        def dump_light_2d(node: Light2D) -> dict[str, Any]:
            return {
                "color": list(node.color),
                "radius": float(node.radius),
                "intensity": float(node.intensity),
                "falloff": float(node.falloff),
                "light_enabled": bool(node.light_enabled),
                "light_mask": int(node.light_mask),
                "cast_shadows": bool(node.cast_shadows),
                "shadow_strength": float(node.shadow_strength),
                "shadow_softness": float(node.shadow_softness),
                "shadow_color": list(node.shadow_color),
                "shadow_mask": int(node.shadow_mask),
                "flicker_enabled": bool(node.flicker_enabled),
                "flicker_strength": float(node.flicker_strength),
                "flicker_speed": float(node.flicker_speed),
                "pulse_enabled": bool(node.pulse_enabled),
                "pulse_amount": float(node.pulse_amount),
                "pulse_speed": float(node.pulse_speed),
                "debug_draw": bool(node.debug_draw),
                "debug_layer": int(node.debug_layer),
            }

        def load_light_2d(
            node: Light2D,
            state: dict[str, Any],
            context: dict[str, Any],
        ) -> None:
            del context
            color = state.get("color", (1.0, 0.85, 0.60))
            node.color = tuple(float(v) for v in color[:3])
            node.radius = float(state.get("radius", 180.0))
            node.intensity = float(state.get("intensity", 1.0))
            node.falloff = float(state.get("falloff", 2.0))
            node.light_enabled = bool(state.get("light_enabled", True))
            node.light_mask = int(state.get("light_mask", 0xFFFFFFFF))
            node.cast_shadows = bool(state.get("cast_shadows", False))
            node.shadow_strength = float(state.get("shadow_strength", 1.0))
            node.shadow_softness = float(state.get("shadow_softness", 0.0))
            shadow_color = state.get("shadow_color", (0.0, 0.0, 0.0))
            node.shadow_color = tuple(float(v) for v in shadow_color[:3])
            node.shadow_mask = int(state.get("shadow_mask", 0xFFFFFFFF))
            node.flicker_enabled = bool(state.get("flicker_enabled", False))
            node.flicker_strength = float(state.get("flicker_strength", 0.12))
            node.flicker_speed = float(state.get("flicker_speed", 17.0))
            node.pulse_enabled = bool(state.get("pulse_enabled", False))
            node.pulse_amount = float(state.get("pulse_amount", 0.15))
            node.pulse_speed = float(state.get("pulse_speed", 2.0))
            node.debug_draw = bool(state.get("debug_draw", False))
            node.debug_layer = int(state.get("debug_layer", 100_000))

        self.register(
            "Light2D",
            Light2D,
            dump_state=dump_light_2d,
            load_state=load_light_2d,
        )

        def dump_light_occluder_2d(node: LightOccluder2D) -> dict[str, Any]:
            return {
                "points": [list(point) for point in node.points],
                "closed": bool(node.closed),
                "occluder_enabled": bool(node.occluder_enabled),
                "occluder_mask": int(node.occluder_mask),
                "debug_draw": bool(node.debug_draw),
                "debug_layer": int(node.debug_layer),
            }

        def load_light_occluder_2d(
            node: LightOccluder2D,
            state: dict[str, Any],
            context: dict[str, Any],
        ) -> None:
            del context
            points = state.get("points", ((-32.0, -32.0), (32.0, -32.0), (32.0, 32.0), (-32.0, 32.0)))
            node.set_polygon(points)
            node.closed = bool(state.get("closed", True))
            node.occluder_enabled = bool(state.get("occluder_enabled", True))
            node.occluder_mask = int(state.get("occluder_mask", 0xFFFFFFFF))
            node.debug_draw = bool(state.get("debug_draw", False))
            node.debug_layer = int(state.get("debug_layer", 100_010))

        self.register(
            "LightOccluder2D",
            LightOccluder2D,
            dump_state=dump_light_occluder_2d,
            load_state=load_light_occluder_2d,
        )

        def dump_tilemap_node(node: TileMapNode) -> dict[str, Any]:
            if node.tilemap is None or node.tileset is None:
                raise ValueError(
                    f"TileMapNode {node.name!r} cannot be serialized without TileMap and TileSet"
                )
            return {
                "tilemap": node.tilemap.to_state(),
                "tileset": node.tileset.to_state(),
                "centered": bool(node.centered),
                "culling_enabled": bool(node.culling_enabled),
                "culling_margin": int(node.culling_margin),
                "base_render_layer": int(node.base_render_layer),
            }

        def load_tilemap_node(
            node: TileMapNode,
            state: dict[str, Any],
            context: dict[str, Any],
        ) -> None:
            tilemap = TileMap.from_state(dict(state["tilemap"]))
            tileset = TileSet.from_state(dict(state["tileset"]))
            assets = context.get("assets")
            if assets is None:
                raise RuntimeError(
                    "Loading a serialized TileMapNode requires context['assets']"
                )
            node.set_map_from_assets(tilemap, tileset, assets)
            node.centered = bool(state.get("centered", True))
            node.culling_enabled = bool(state.get("culling_enabled", True))
            node.culling_margin = int(state.get("culling_margin", 1))
            node.base_render_layer = int(state.get("base_render_layer", 0))

        self.register(
            "TileMapNode",
            TileMapNode,
            dump_state=dump_tilemap_node,
            load_state=load_tilemap_node,
        )
