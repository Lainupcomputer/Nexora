"""Contract tests for the shared standalone-editor UI package."""

from pathlib import Path

from nexora.editor import standalone_ui
from nexora.editor import ui
from nexora.editor.model import EditorProjectContext
from nexora.editor.standalone_tilemap_editor import StandaloneTileMapEditorApp


def test_shared_ui_package_exports_the_legacy_widget_surface() -> None:
    for name in ui.__all__:
        assert getattr(ui, name) is getattr(standalone_ui, name)


def test_shared_ui_package_exposes_the_common_editor_controls() -> None:
    assert {"Button", "Menu", "TextField", "ListBox"}.issubset(ui.__all__)


def test_file_browser_model_confines_navigation_and_filters_files(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    nested = assets / "nested"
    nested.mkdir(parents=True)
    (assets / "tileset.png").write_bytes(b"")
    (assets / "ignore.txt").write_text("ignored", encoding="utf-8")
    (nested / "nested.png").write_bytes(b"")

    browser = ui.FileBrowserModel()
    browser.open(tmp_path, start=assets, extensions=(".png",))

    assert browser.labels == ["[..]", "[nested]", "tileset.png"]
    assert browser.select(1) is None
    assert browser.path == nested.resolve()
    assert browser.labels == ["[..]", "nested.png"]
    assert browser.select(0) is None
    assert browser.path == assets.resolve()


def test_standalone_tilemap_editor_is_the_only_tilemap_editor_entrypoint() -> None:
    from nexora.editor import run_standalone_tilemap_editor

    assert StandaloneTileMapEditorApp.__name__ == "StandaloneTileMapEditorApp"
    assert callable(run_standalone_tilemap_editor)


def test_project_context_provides_shared_editor_roots(tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "items").mkdir()
    (tmp_path / "cutscenes").mkdir()

    context = EditorProjectContext.from_path(tmp_path)

    assert context.root == tmp_path.resolve()
    assert context.assets_root == (tmp_path / "assets").resolve()
    assert context.items_root == (tmp_path / "items").resolve()
    assert context.cutscenes_root == (tmp_path / "cutscenes").resolve()
