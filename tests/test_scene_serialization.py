from __future__ import annotations

from pathlib import Path

import pytest

from nexora.nodes import Node
from nexora.nodes.entity import (
    CharacterBody2D,
    CollisionShape2D,
    StaticBody2D,
)
from nexora.scene import Scene
from nexora.scene.serialization import (
    NodeFactoryRegistry,
    PrefabSerializer,
    SceneIntegrityError,
    SceneSerializer,
    UnregisteredNodeTypeError,
)


KEY = b"nexora-scene-test-signing-key-0123456789abcdef"


def test_scene_round_trip(tmp_path: Path) -> None:
    scene = Scene("Beach")
    scene.asset_groups = ["core", "player", "beach"]
    scene.serialization_metadata = {"spawn": "shore"}

    player = CharacterBody2D("Player", scene.world)
    player.transform.x = 12.5
    player.transform.y = -8.0
    player.velocity.set(3.0, 4.0)
    scene.root.add_child(player)

    shape = CollisionShape2D("Collider", scene.world, 20.0, 42.0)
    shape.disabled = True
    player.add_child(shape)

    wall = StaticBody2D("Wall", scene.world)
    wall.transform.rotation = 15.0
    scene.root.add_child(wall)

    serializer = SceneSerializer(signing_key=KEY)
    path = serializer.save(scene, tmp_path / "beach")
    loaded = serializer.load(path)

    assert path.suffix == ".nxscene"
    assert loaded.name == "Beach"
    assert loaded.asset_groups == ["core", "player", "beach"]
    assert loaded.serialization_metadata == {"spawn": "shore"}
    assert len(loaded.root.children) == 2

    loaded_player = loaded.root.children[0]
    assert isinstance(loaded_player, CharacterBody2D)
    assert loaded_player.transform.x == 12.5
    assert loaded_player.transform.y == -8.0
    assert loaded_player.velocity.tuple == (3.0, 4.0)

    loaded_shape = loaded_player.children[0]
    assert isinstance(loaded_shape, CollisionShape2D)
    assert loaded_shape.width == 20.0
    assert loaded_shape.height == 42.0
    assert loaded_shape.disabled is True


def test_prefab_round_trip_and_overrides(tmp_path: Path) -> None:
    scene = Scene("PrefabSource")
    root = StaticBody2D("Crate", scene.world)
    root.transform.x = 2.0
    shape = CollisionShape2D("Collider", scene.world, 32.0, 32.0)
    root.add_child(shape)

    prefabs = PrefabSerializer(signing_key=KEY)
    path = prefabs.save(root, tmp_path / "crate")

    target = Scene("Target")
    instance = prefabs.instantiate(
        path,
        target.world,
        parent=target.root,
        overrides={
            "name": "CrateInstance",
            "transform": {"x": 100.0, "y": 50.0},
        },
    )

    assert path.suffix == ".nxprefab"
    assert instance.name == "CrateInstance"
    assert instance.transform.x == 100.0
    assert instance.transform.y == 50.0
    assert len(instance.children) == 1


def test_tampered_scene_is_rejected(tmp_path: Path) -> None:
    scene = Scene("Safe")
    serializer = SceneSerializer(signing_key=KEY)
    path = serializer.save(scene, tmp_path / "safe.nxscene")

    raw = bytearray(path.read_bytes())
    raw[-1] ^= 0x01
    path.write_bytes(raw)

    with pytest.raises(SceneIntegrityError):
        serializer.load(path)


def test_unregistered_node_is_rejected() -> None:
    class CustomNode(Node):
        pass

    scene = Scene("Custom")
    scene.root.add_child(CustomNode("Custom", scene.world))

    serializer = SceneSerializer(signing_key=KEY)

    with pytest.raises(UnregisteredNodeTypeError):
        serializer.encode(scene)


def test_custom_node_registry_round_trip(tmp_path: Path) -> None:
    class CustomNode(Node):
        def __init__(self, name, world):
            super().__init__(name, world)
            self.value = 0

    registry = NodeFactoryRegistry()
    registry.register(
        "TestCustomNode",
        CustomNode,
        dump_state=lambda node: {"value": int(node.value)},
        load_state=lambda node, state, context: setattr(
            node, "value", int(state.get("value", 0))
        ),
    )

    scene = Scene("Custom")
    custom = CustomNode("Thing", scene.world)
    custom.value = 123
    scene.root.add_child(custom)

    serializer = SceneSerializer(signing_key=KEY, registry=registry)
    path = serializer.save(scene, tmp_path / "custom.nxscene")
    loaded = serializer.load(path)

    loaded_custom = loaded.root.children[0]
    assert isinstance(loaded_custom, CustomNode)
    assert loaded_custom.value == 123


def test_scene_metadata_can_be_inspected_before_node_construction(tmp_path: Path) -> None:
    scene = Scene("HQ")
    scene.asset_groups = ["core", "hq"]
    scene.serialization_metadata = {"kind": "safe_zone"}

    serializer = SceneSerializer(signing_key=KEY)
    path = serializer.save(scene, tmp_path / "hq.nxscene")

    metadata = serializer.inspect_metadata(path)
    assert metadata == {
        "name": "HQ",
        "schema_version": 1,
        "asset_groups": ["core", "hq"],
        "metadata": {"kind": "safe_zone"},
    }
