from __future__ import annotations

from pathlib import Path
from typing import Any

from nexora.nodes.node import Node

from .codec import PREFAB_MAGIC, decode_secure_pickle, encode_secure_pickle
from .common import apply_common_node_state, atomic_write, node_to_state
from .migrations import MigrationRegistry
from .registry import NodeFactoryRegistry


PREFAB_SCHEMA_VERSION = 1


class PrefabSerializer:
    FILE_EXTENSION = ".nxprefab"

    def __init__(
        self,
        *,
        signing_key: bytes | str,
        registry: NodeFactoryRegistry | None = None,
        max_file_size: int = 64 * 1024 * 1024,
    ) -> None:
        self.signing_key = signing_key
        self.registry = registry or NodeFactoryRegistry()
        self.max_file_size = int(max_file_size)
        self.migrations = MigrationRegistry(PREFAB_SCHEMA_VERSION)

    def to_state(self, node: Node) -> dict[str, Any]:
        return {
            "schema_version": PREFAB_SCHEMA_VERSION,
            "format": "nexora_prefab",
            "root": node_to_state(node, self.registry),
        }

    def encode(self, node: Node) -> bytes:
        return encode_secure_pickle(
            self.to_state(node),
            signing_key=self.signing_key,
            magic=PREFAB_MAGIC,
        )

    def save(self, node: Node, path: str | Path) -> Path:
        path = Path(path)
        if path.suffix == "":
            path = path.with_suffix(self.FILE_EXTENSION)
        atomic_write(path, self.encode(node))
        return path

    def decode_state(self, raw: bytes) -> dict[str, Any]:
        state = decode_secure_pickle(
            raw,
            signing_key=self.signing_key,
            expected_magic=PREFAB_MAGIC,
            max_payload_size=self.max_file_size,
        )
        if not isinstance(state, dict) or state.get("format") != "nexora_prefab":
            raise ValueError("Payload is not a Nexora prefab state.")
        return self.migrations.migrate(state)

    def load_state(self, path: str | Path) -> dict[str, Any]:
        return self.decode_state(Path(path).read_bytes())

    def instantiate(
        self,
        path: str | Path,
        world,
        *,
        parent: Node | None = None,
        context: dict[str, Any] | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> Node:
        state = self.load_state(path)
        root_state = dict(state["root"])
        if overrides:
            root_state = _merge_root_overrides(root_state, overrides)

        node = self._build_node(root_state, world, context=context or {})
        setattr(node, "_nexora_prefab_source", str(Path(path)))
        setattr(node, "_nexora_prefab_overrides", dict(overrides or {}))
        if parent is not None:
            parent.add_child(node)
        return node

    def _build_node(
        self,
        state: dict[str, Any],
        world,
        *,
        context: dict[str, Any],
        id_lookup: dict[str, Node] | None = None,
    ) -> Node:
        if id_lookup is None:
            id_lookup = {}

        node = self.registry.create(
            state["type"],
            state.get("name", "Node"),
            world,
            context=context,
        )
        apply_common_node_state(node, state)
        self.registry.load_properties(
            node,
            dict(state.get("properties", {})),
            context=context,
        )

        node_id = str(state.get("id", ""))
        if node_id:
            id_lookup[node_id] = node

        for child_state in state.get("children", []):
            child = self._build_node(
                dict(child_state),
                world,
                context=context,
                id_lookup=id_lookup,
            )
            node.add_child(child)

        return node


def _merge_root_overrides(
    state: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    result = dict(state)
    for key in ("name", "enabled", "visible"):
        if key in overrides:
            result[key] = overrides[key]

    if "transform" in overrides:
        transform = dict(result.get("transform", {}))
        transform.update(dict(overrides["transform"]))
        result["transform"] = transform

    if "properties" in overrides:
        properties = dict(result.get("properties", {}))
        properties.update(dict(overrides["properties"]))
        result["properties"] = properties

    return result
