from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from nexora.nodes.node import Node

from .errors import UnregisteredNodeTypeError


Factory = Callable[
    [str, Any, dict[str, Any]],
    Node,
]

DumpState = Callable[
    [Node],
    dict[str, Any],
]

LoadState = Callable[
    [
        Node,
        dict[str, Any],
        dict[str, Any],
    ],
    None,
]


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

    Files contain only a string type id.

    Loading never imports a class from a path stored in the
    file. A type must already be registered here.
    """

    def __init__(
        self,
        *,
        register_defaults: bool = True,
    ) -> None:
        self._by_id: dict[
            str,
            NodeAdapter,
        ] = {}

        self._by_type: dict[
            type[Node],
            NodeAdapter,
        ] = {}

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
        type_id = str(
            type_id
        ).strip()

        if not type_id:
            raise ValueError(
                "type_id cannot be empty"
            )

        if not issubclass(
            node_type,
            Node,
        ):
            raise TypeError(
                "node_type must inherit from Node"
            )

        if type_id in self._by_id:
            raise ValueError(
                "Node type id already registered: "
                f"{type_id}"
            )

        if factory is None:

            def factory(
                name,
                world,
                context,
                cls=node_type,
            ):
                return cls(
                    name,
                    world,
                )

        if dump_state is None:
            dump_state = (
                lambda node: {}
            )

        if load_state is None:
            load_state = (
                lambda node, state, context: None
            )

        adapter = NodeAdapter(
            type_id=type_id,
            node_type=node_type,
            factory=factory,
            dump_state=dump_state,
            load_state=load_state,
        )

        self._by_id[
            type_id
        ] = adapter

        self._by_type[
            node_type
        ] = adapter

    def adapter_for_node(
        self,
        node: Node,
    ) -> NodeAdapter:
        adapter = self._by_type.get(
            type(node)
        )

        if adapter is None:
            raise UnregisteredNodeTypeError(
                "Node type is not registered: "
                f"{type(node).__module__}."
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
        adapter = self._by_id.get(
            str(type_id)
        )

        if adapter is None:
            raise UnregisteredNodeTypeError(
                "Node type id is not registered: "
                f"{type_id!r}"
            )

        return adapter.factory(
            str(name),
            world,
            context or {},
        )

    def dump_properties(
        self,
        node: Node,
    ) -> dict[str, Any]:
        return dict(
            self.adapter_for_node(
                node
            ).dump_state(
                node
            )
        )

    def load_properties(
        self,
        node: Node,
        state: dict[str, Any],
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.adapter_for_node(
            node
        ).load_state(
            node,
            dict(state),
            context or {},
        )

    def type_id_for(
        self,
        node: Node,
    ) -> str:
        return self.adapter_for_node(
            node
        ).type_id

    def registered_type_ids(
        self,
    ) -> tuple[str, ...]:
        """
        Return all registered node type IDs
        in stable sorted order.
        """

        return tuple(
            sorted(
                self._by_id.keys()
            )
        )

    def _register_defaults(
        self,
    ) -> None:
        from .defaults import register_default_nodes

        register_default_nodes(self)
