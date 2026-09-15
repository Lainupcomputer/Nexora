from __future__ import annotations

from pathlib import Path
from typing import Any

from nexora.nodes.node import Node

from .registry import NodeFactoryRegistry


def node_to_state(
    node: Node,
    registry: NodeFactoryRegistry,
    *,
    id_map: dict[Node, str] | None = None,
) -> dict[str, Any]:
    if id_map is None:
        id_map = {}

    node_id = id_map.get(node)
    if node_id is None:
        node_id = f"node_{len(id_map) + 1}"
        id_map[node] = node_id

    return {
        "kind": "node",
        "id": node_id,
        "type": registry.type_id_for(node),
        "name": str(node.name),
        "enabled": bool(node.enabled),
        "visible": bool(node.visible),
        "transform": {
            "x": float(node.transform.x),
            "y": float(node.transform.y),
            "rotation": float(node.transform.rotation),
            "scale_x": float(node.transform.scale_x),
            "scale_y": float(node.transform.scale_y),
        },
        "properties": registry.dump_properties(node),
        "children": [
            node_to_state(child, registry, id_map=id_map)
            for child in node.children
        ],
    }


def apply_common_node_state(node: Node, state: dict[str, Any]) -> None:
    node.enabled = bool(state.get("enabled", True))
    node.visible = bool(state.get("visible", True))

    transform = dict(state.get("transform", {}))
    node.transform.x = float(transform.get("x", 0.0))
    node.transform.y = float(transform.get("y", 0.0))
    node.transform.rotation = float(transform.get("rotation", 0.0))
    node.transform.scale_x = float(transform.get("scale_x", 1.0))
    node.transform.scale_y = float(transform.get("scale_y", 1.0))


def atomic_write(path: Path, raw: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(raw)
    temporary.replace(path)
