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
