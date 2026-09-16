from pathlib import Path

import pytest

from nexora.editor.model.document import EditorDocument
from nexora.scene import Scene


class FakeSerializer:
    def __init__(self) -> None:
        self.saved = []

    def save(self, scene, path):
        path = Path(path)
        if path.suffix == "":
            path = path.with_suffix(".nxscene")
        self.saved.append((scene, path))
        return path

    def load(self, path):
        return Scene(Path(path).stem)


def test_new_scene_marks_document_dirty():
    doc = EditorDocument()
    old_scene = doc.scene
    scene = doc.new("LevelOne")

    assert scene is doc.scene
    assert scene.name == "LevelOne"
    assert doc.path is None
    assert doc.dirty
    assert doc.title == "LevelOne *"
    assert old_scene.destroyed


def test_save_as_sets_path_and_clears_dirty(tmp_path):
    doc = EditorDocument(Scene("LevelOne"))
    doc.mark_dirty()
    serializer = FakeSerializer()

    path = doc.save_as(serializer, tmp_path / "level_one")

    assert path == (tmp_path / "level_one.nxscene").resolve()
    assert doc.path == path
    assert not doc.dirty


def test_save_requires_existing_document_path():
    doc = EditorDocument(Scene("Untitled"))

    with pytest.raises(ValueError):
        doc.save(FakeSerializer())


def test_load_replaces_scene_and_clears_dirty(tmp_path):
    doc = EditorDocument(Scene("Old"))
    old_scene = doc.scene
    doc.mark_dirty()
    serializer = FakeSerializer()
    path = tmp_path / "loaded.nxscene"

    scene = doc.load(serializer, path)

    assert scene is doc.scene
    assert doc.display_name == "loaded"
    assert doc.path == path.resolve()
    assert not doc.dirty
    assert old_scene.destroyed
