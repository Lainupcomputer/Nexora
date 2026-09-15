from __future__ import annotations

from pathlib import Path
from typing import Any

from nexora.scene.scene import Scene

from .codec import SCENE_MAGIC, decode_secure_pickle, encode_secure_pickle
from .common import apply_common_node_state, atomic_write, node_to_state
from .migrations import MigrationRegistry
from .prefab import PrefabSerializer
from .registry import NodeFactoryRegistry


SCENE_SCHEMA_VERSION = 1


class SceneLoadResult:
    """Mutable result holder for SceneLoadTask integration."""

    def __init__(self, metadata: dict[str, Any]) -> None:
        self.metadata = metadata
        self.scene: Scene | None = None


class SceneSerializer:
    FILE_EXTENSION = ".nxscene"

    def __init__(
        self,
        *,
        signing_key: bytes | str,
        registry: NodeFactoryRegistry | None = None,
        max_file_size: int = 128 * 1024 * 1024,
    ) -> None:
        self.signing_key = signing_key
        self.registry = registry or NodeFactoryRegistry()
        self.max_file_size = int(max_file_size)
        self.migrations = MigrationRegistry(SCENE_SCHEMA_VERSION)
        self.prefabs = PrefabSerializer(
            signing_key=signing_key,
            registry=self.registry,
            max_file_size=max_file_size,
        )

    def to_state(self, scene: Scene) -> dict[str, Any]:
        id_map = {}
        root_children = [
            self._node_or_prefab_to_state(child, id_map=id_map)
            for child in scene.root.children
        ]
        ui_children = [
            self._node_or_prefab_to_state(child, id_map=id_map)
            for child in scene.ui.children
        ]

        camera_id = None
        if scene.camera is not None:
            camera_id = id_map.get(scene.camera)

        return {
            "schema_version": SCENE_SCHEMA_VERSION,
            "format": "nexora_scene",
            "name": str(scene.name),
            "asset_groups": list(getattr(scene, "asset_groups", ())),
            "metadata": dict(getattr(scene, "serialization_metadata", {})),
            "camera_id": camera_id,
            "root_children": root_children,
            "ui_children": ui_children,
        }

    def _node_or_prefab_to_state(self, node, *, id_map):
        source = getattr(node, "_nexora_prefab_source", None)
        if source:
            return {
                "kind": "prefab",
                "source": str(source),
                "overrides": dict(
                    getattr(node, "_nexora_prefab_overrides", {})
                ),
            }
        return node_to_state(node, self.registry, id_map=id_map)

    def encode(self, scene: Scene) -> bytes:
        return encode_secure_pickle(
            self.to_state(scene),
            signing_key=self.signing_key,
            magic=SCENE_MAGIC,
        )

    def save(self, scene: Scene, path: str | Path) -> Path:
        path = Path(path)
        if path.suffix == "":
            path = path.with_suffix(self.FILE_EXTENSION)
        atomic_write(path, self.encode(scene))
        return path

    def decode_state(self, raw: bytes) -> dict[str, Any]:
        state = decode_secure_pickle(
            raw,
            signing_key=self.signing_key,
            expected_magic=SCENE_MAGIC,
            max_payload_size=self.max_file_size,
        )
        if not isinstance(state, dict) or state.get("format") != "nexora_scene":
            raise ValueError("Payload is not a Nexora scene state.")
        return self.migrations.migrate(state)

    def load_state(self, path: str | Path) -> dict[str, Any]:
        return self.decode_state(Path(path).read_bytes())

    def inspect_metadata(self, path: str | Path) -> dict[str, Any]:
        """Read scene metadata without constructing any Node objects."""
        state = self.load_state(path)
        return {
            "name": str(state.get("name", "Scene")),
            "schema_version": int(state.get("schema_version", 1)),
            "asset_groups": list(state.get("asset_groups", [])),
            "metadata": dict(state.get("metadata", {})),
        }

    def add_to_load_task(
        self,
        task,
        assets,
        path: str | Path,
        *,
        context: dict[str, Any] | None = None,
        asset_callbacks=None,
        on_loaded=None,
        force_reload_assets: bool = False,
        construct_weight: float = 0.25,
    ) -> SceneLoadResult:
        """Integrate a serialized scene with the existing LoadingScene flow.

        The scene container is authenticated and inspected first. Its declared
        asset groups are appended to the task in file order. The actual node
        tree is constructed only after those asset stages have completed.
        """
        path = Path(path)
        metadata = self.inspect_metadata(path)
        result = SceneLoadResult(metadata)

        for group_name in metadata["asset_groups"]:
            assets.add_group_loading_stages(
                task,
                group_name,
                callbacks=asset_callbacks,
                force_reload=force_reload_assets,
            )

        def construct_scene() -> None:
            result.scene = self.load(path, context=context)
            if on_loaded is not None:
                on_loaded(result.scene)

        task.add_stage(
            "scene_construct",
            weight=max(0.0001, float(construct_weight)),
            status=f"Initialisiere Szene: {metadata['name']}",
            callback=construct_scene,
        )

        return result

    def load(
        self,
        path: str | Path,
        *,
        context: dict[str, Any] | None = None,
    ) -> Scene:
        path = Path(path)
        state = self.load_state(path)
        scene = Scene(str(state.get("name", path.stem)))
        scene.asset_groups = list(state.get("asset_groups", []))
        scene.serialization_metadata = dict(state.get("metadata", {}))

        context_data = dict(context or {})
        context_data.setdefault("scene_path", str(path))
        context_data.setdefault("scene", scene)

        id_lookup: dict[str, Any] = {}

        for child_state in state.get("root_children", []):
            child = self._build_entry(
                dict(child_state),
                scene,
                scene.root,
                path.parent,
                context_data,
                id_lookup,
            )
            if child.parent is None:
                scene.root.add_child(child)

        for child_state in state.get("ui_children", []):
            child = self._build_entry(
                dict(child_state),
                scene,
                scene.ui,
                path.parent,
                context_data,
                id_lookup,
            )
            if child.parent is None:
                scene.ui.add_child(child)

        camera_id = state.get("camera_id")
        if camera_id and camera_id in id_lookup:
            scene.camera = id_lookup[camera_id]

        return scene

    def _build_entry(
        self,
        state: dict[str, Any],
        scene: Scene,
        parent,
        base_dir: Path,
        context: dict[str, Any],
        id_lookup: dict[str, Any],
    ):
        kind = state.get("kind", "node")

        if kind == "prefab":
            source = Path(str(state["source"]))
            if not source.is_absolute():
                source = base_dir / source
            node = self.prefabs.instantiate(
                source,
                scene.world,
                context=context,
                overrides=dict(state.get("overrides", {})),
            )
            parent.add_child(node)
            return node

        node = self.registry.create(
            state["type"],
            state.get("name", "Node"),
            scene.world,
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

        parent.add_child(node)
        for child_state in state.get("children", []):
            self._build_entry(
                dict(child_state),
                scene,
                node,
                base_dir,
                context,
                id_lookup,
            )
        return node
