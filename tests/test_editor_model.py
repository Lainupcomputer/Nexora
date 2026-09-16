from __future__ import annotations

from nexora.nodes import Node
from nexora.editor.model import (
    EditorDocument,
    ProjectModel,
    SelectionService,
)


def test_project_model_discovers_scenes_and_assets(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "icon.png").write_bytes(b"png")
    (tmp_path / "scenes").mkdir()
    (tmp_path / "scenes" / "main.nxscene").write_bytes(b"scene")

    model = ProjectModel(tmp_path)

    assert len(model.iter_scene_files()) == 1
    assert len(model.iter_assets()) == 1
    assert model.iter_assets()[0].relative_path.as_posix() == "assets/icon.png"


def test_editor_document_exposes_world_and_ui_roots():
    document = EditorDocument()
    entries = document.iter_tree_entries()

    assert entries[0].node is document.scene.root
    assert entries[0].branch == "world"
    assert entries[1].node is document.scene.ui
    assert entries[1].branch == "ui"


def test_editor_document_flattens_node_hierarchy():
    document = EditorDocument()
    parent = Node("Player", document.scene.world)
    child = Node("Weapon", document.scene.world)
    parent.add_child(child)
    document.scene.root.add_child(parent)

    entries = document.iter_tree_entries()
    names = [entry.node.name for entry in entries]
    depths = [entry.depth for entry in entries]

    assert names[:3] == ["Root", "Player", "Weapon"]
    assert depths[:3] == [0, 1, 2]


def test_selection_service_emits_previous_and_current():
    selection = SelectionService()
    calls = []
    a = object()
    b = object()

    selection.changed.connect(
        lambda current, previous: calls.append((current, previous))
    )

    assert selection.select(a)
    assert not selection.select(a)
    assert selection.select(b)
    assert selection.clear()

    assert calls == [
        (a, None),
        (b, a),
        (None, b),
    ]
