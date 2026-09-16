from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from nexora.editor.app import EditorApp
from nexora.editor.model import EditorDocument
from nexora.nodes.entity import StaticBody2D
from nexora.scene import Scene
from nexora.scene.serialization import SceneSerializer


KEY = b"nexora-editor-play-test-signing-key-0123456789"


class FakeSceneManager:
    def __init__(self, editor_scene) -> None:
        self.loaded = {editor_scene.name: editor_scene}
        self.active = editor_scene

    def get(self, name):
        return self.loaded.get(name)

    def load(self, scene, *, activate=False):
        self.loaded[scene.name] = scene
        if activate:
            self.active = scene
        return scene

    def change_scene(self, name, *, unload_previous=None):
        previous = self.active
        self.active = self.loaded[name]
        if unload_previous and previous is not self.active:
            self.loaded.pop(previous.name, None)
            previous.destroy()
        return self.active


class FakeEditorScene:
    name = "NexoraEditor"

    def __init__(self) -> None:
        self.play_button = SimpleNamespace(text="Run")
        self.status_label = SimpleNamespace(text="Ready")
        self.sync_calls = 0
        self.errors = []
        self.refresh_calls = 0

    def _sync_all_prefab_instance_overrides(self) -> None:
        self.sync_calls += 1

    def _show_error(self, message: str) -> None:
        self.errors.append(message)

    def _refresh_document_ui(self) -> None:
        self.refresh_calls += 1


class FakeInput:
    def key_pressed(self, key: str) -> bool:
        return key == "f8"


def test_editor_play_mode_runs_an_isolated_scene_copy(tmp_path: Path) -> None:
    source = Scene("Preview")
    body = StaticBody2D("Player", source.world)
    body.transform.x = 24.0
    source.root.add_child(body)

    editor_scene = FakeEditorScene()
    app = object.__new__(EditorApp)
    app.editor_project_path = tmp_path
    app.editor_scene = editor_scene
    app.editor_document = EditorDocument(source)
    app._scene_serializer = SceneSerializer(signing_key=KEY)
    app._scenes = FakeSceneManager(editor_scene)
    app.engine = None
    app.renderer = None
    app.input = None
    app._play_scene = None
    app._play_mode = False

    app.start_play_mode()

    assert app.play_mode is True
    assert editor_scene.sync_calls == 1
    assert editor_scene.play_button.text == "Stop"
    runtime_scene = app._play_scene
    assert runtime_scene is not source
    assert runtime_scene.root.children[0] is not body
    assert runtime_scene.root.children[0].transform.x == 24.0

    app.input = FakeInput()
    app.update(0.0)

    assert app.play_mode is False
    assert app._play_scene is None
    assert editor_scene.play_button.text == "Run"
    assert editor_scene.status_label.text == "Play mode stopped"
    assert runtime_scene.destroyed is True
    assert editor_scene.errors == []
