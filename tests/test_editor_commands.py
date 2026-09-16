from pathlib import Path

from nexora.editor.commands import (
    AddNodeCommand,
    CommandStack,
    DeleteNodeCommand,
    InstantiatePrefabCommand,
    RenameNodeCommand,
)
from nexora.nodes.entity import CollisionShape2D, StaticBody2D
from nexora.scene import Scene
from nexora.scene.serialization import (
    NodeFactoryRegistry,
    PrefabSerializer,
    SceneSerializer,
)


KEY = b"nexora-editor-test-signing-key-0123456789"


def test_command_stack_add_undo_redo():
    scene = Scene("EditorTest")
    registry = NodeFactoryRegistry()
    stack = CommandStack()

    command = AddNodeCommand(
        parent=scene.root,
        registry=registry,
        type_id="Node",
        name="Player",
    )
    node = stack.execute(command)
    assert node.name == "Player"
    assert scene.root.find_child("Player") is node

    stack.undo()
    assert scene.root.find_child("Player") is None

    restored = stack.redo()
    assert restored is not None
    assert restored.name == "Player"
    assert scene.root.find_child("Player") is restored


def test_delete_command_restores_subtree_and_order():
    scene = Scene("EditorTest")
    registry = NodeFactoryRegistry()

    a = registry.create("Node", "A", scene.world)
    target = registry.create("Node", "Target", scene.world)
    child = registry.create("Node", "Child", scene.world)
    b = registry.create("Node", "B", scene.world)
    target.add_child(child)
    scene.root.add_child(a)
    scene.root.add_child(target)
    scene.root.add_child(b)

    command = DeleteNodeCommand(node=target, registry=registry)
    command.execute()
    assert [node.name for node in scene.root.children] == ["A", "B"]

    restored = command.undo()
    assert [node.name for node in scene.root.children] == ["A", "Target", "B"]
    assert restored.children[0].name == "Child"


def test_rename_command_undo_redo():
    scene = Scene("EditorTest")
    registry = NodeFactoryRegistry()
    node = registry.create("Node", "Old", scene.world)
    scene.root.add_child(node)
    stack = CommandStack()

    stack.execute(RenameNodeCommand(node, "New"))
    assert node.name == "New"
    stack.undo()
    assert node.name == "Old"
    stack.redo()
    assert node.name == "New"


def test_registry_exposes_safe_type_ids():
    registry = NodeFactoryRegistry()
    type_ids = registry.registered_type_ids()
    assert "Node" in type_ids
    assert "CharacterBody2D" in type_ids


def test_prefab_instance_command_supports_undo_redo_and_scene_round_trip(
    tmp_path: Path,
):
    registry = NodeFactoryRegistry()
    prefabs = PrefabSerializer(
        signing_key=KEY,
        registry=registry,
    )

    source_scene = Scene("PrefabSource")
    crate = StaticBody2D("Crate", source_scene.world)
    crate.transform.rotation = 15.0
    crate.add_child(
        CollisionShape2D(
            "Collider",
            source_scene.world,
            32.0,
            32.0,
        )
    )
    prefab_path = prefabs.save(crate, tmp_path / "crate")

    target_scene = Scene("Target")
    stack = CommandStack()
    command = InstantiatePrefabCommand(
        parent=target_scene.root,
        prefab_serializer=prefabs,
        registry=registry,
        prefab_path=prefab_path,
        name="CrateInstance",
        x=100.0,
        y=50.0,
    )

    instance = stack.execute(command)
    assert instance.name == "CrateInstance"
    assert instance.transform.x == 100.0
    assert instance.transform.y == 50.0
    assert len(instance.children) == 1

    instance.transform.rotation = 42.0
    instance.enabled = False
    instance.name = "MovedCrate"

    stack.undo()
    assert target_scene.root.find_child("MovedCrate") is None

    restored = stack.redo()
    assert restored.name == "MovedCrate"
    assert restored.transform.x == 100.0
    assert restored.transform.y == 50.0
    assert restored.transform.rotation == 42.0
    assert restored.enabled is False
    assert len(restored.children) == 1

    scenes = SceneSerializer(
        signing_key=KEY,
        registry=registry,
    )
    scene_path = scenes.save(target_scene, tmp_path / "target")
    loaded = scenes.load(scene_path)
    loaded_instance = loaded.root.children[0]

    assert loaded_instance.name == "MovedCrate"
    assert loaded_instance.transform.x == 100.0
    assert loaded_instance.transform.y == 50.0
    assert loaded_instance.transform.rotation == 42.0
    assert loaded_instance.enabled is False
    assert getattr(loaded_instance, "_nexora_prefab_source") == str(
        prefab_path.resolve()
    )
