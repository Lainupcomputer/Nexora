from __future__ import annotations

from copy import deepcopy

from nexora.scene.serialization.common import apply_common_node_state


def insert_child(parent, child, index: int) -> None:
    """Insert *child* into *parent* at a stable child index."""

    parent.add_child(child)
    children = parent.children
    if child in children:
        children.remove(child)
    index = max(0, min(int(index), len(children)))
    children.insert(index, child)


def build_node_from_state(state, world, registry, *, context=None):
    """Rebuild a serialized editor node subtree through the shared registry."""

    data = deepcopy(dict(state))
    load_context = context or {}
    node = registry.create(
        data["type"],
        data.get("name", "Node"),
        world,
        context=load_context,
    )
    apply_common_node_state(node, data)
    registry.load_properties(
        node,
        dict(data.get("properties", {})),
        context=load_context,
    )
    for child_state in data.get("children", []):
        child = build_node_from_state(
            child_state,
            world,
            registry,
            context=load_context,
        )
        node.add_child(child)
    return node
