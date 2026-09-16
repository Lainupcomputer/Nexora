from nexora.editor.commands import (
    AddNodeCommand,
    CommandStack,
    DeleteNodeCommand,
    RenameNodeCommand,
)
from nexora.scene import Scene
from nexora.scene.serialization import NodeFactoryRegistry


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
