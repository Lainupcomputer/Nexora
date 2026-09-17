from types import SimpleNamespace

from nexora.editor.scene import EditorScene


def test_focus_selected_node_centers_viewport() -> None:
    node = SimpleNamespace(
        name="Hero",
        world_position=(128.0, -64.0),
    )
    scene = EditorScene.__new__(EditorScene)
    scene.selection = SimpleNamespace(selected=node)
    scene.document = SimpleNamespace(
        scene=SimpleNamespace(root=object(), ui=object())
    )
    scene.viewport_state = SimpleNamespace(x=0.0, y=0.0)
    scene.status_label = SimpleNamespace(text="")

    scene._focus_selected_node()

    assert scene.viewport_state.x == 128.0
    assert scene.viewport_state.y == -64.0
    assert scene.status_label.text == "Focused Hero"


def test_focus_without_selection_reports_status() -> None:
    scene = EditorScene.__new__(EditorScene)
    scene.selection = SimpleNamespace(selected=None)
    scene.document = SimpleNamespace(
        scene=SimpleNamespace(root=object(), ui=object())
    )
    scene.status_label = SimpleNamespace(text="")

    scene._focus_selected_node()

    assert scene.status_label.text == "Select a node to focus"
