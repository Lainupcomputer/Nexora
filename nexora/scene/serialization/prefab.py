from __future__ import annotations

from pathlib import Path
from typing import Any

from nexora.nodes.node import Node
from nexora.data.codecs import prefab as prefab_codec
from nexora.data.errors import DataIntegrityError, DataError

from .common import apply_common_node_state, node_to_state
from .errors import InvalidSceneFileError, SceneIntegrityError, UnsupportedSceneVersionError
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

    def to_state(self, node: Node) -> dict[str, Any]:
        return {
            "root": node_to_state(node, self.registry),
        }

    def encode(self, node: Node) -> bytes:
        return prefab_codec.encode_state(
            self.to_state(node),
            version=PREFAB_SCHEMA_VERSION,
            signing_key=self.signing_key,
        )

    def save(self, node: Node, path: str | Path) -> Path:
        path = Path(path)
        if path.suffix == "":
            path = path.with_suffix(self.FILE_EXTENSION)
        try:
            return prefab_codec.save_state(
                self.to_state(node),
                path,
                version=PREFAB_SCHEMA_VERSION,
                signing_key=self.signing_key,
                max_file_size=self.max_file_size,
            )
        except DataIntegrityError as exc:
            raise SceneIntegrityError(str(exc)) from exc
        except DataError as exc:
            raise InvalidSceneFileError(str(exc)) from exc

    def decode_state(self, raw: bytes) -> dict[str, Any]:
        try:
            state = prefab_codec.decode_state(
                raw,
                version=PREFAB_SCHEMA_VERSION,
                signing_key=self.signing_key,
                max_file_size=self.max_file_size,
            )
        except DataIntegrityError as exc:
            raise SceneIntegrityError(str(exc)) from exc
        except DataError as exc:
            raise InvalidSceneFileError(str(exc)) from exc
        return state

    def load_state(self, path: str | Path) -> dict[str, Any]:
        try:
            state = prefab_codec.load_state(
                path,
                version=PREFAB_SCHEMA_VERSION,
                signing_key=self.signing_key,
                max_file_size=self.max_file_size,
            )
        except DataIntegrityError as exc:
            raise SceneIntegrityError(str(exc)) from exc
        except DataError as exc:
            raise InvalidSceneFileError(str(exc)) from exc
        return state

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
