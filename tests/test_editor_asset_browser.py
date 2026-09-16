from __future__ import annotations

from pathlib import Path

import pytest

from nexora.editor.asset_browser import (
    AssetBrowserModel,
    classify_asset,
    format_file_size,
)


def test_classify_asset(tmp_path: Path):
    image = tmp_path / "hero.png"
    image.write_bytes(b"x")

    scene = tmp_path / "main.nxscene"
    scene.write_text("{}", encoding="utf-8")

    prefab = tmp_path / "enemy.nxprefab"
    prefab.write_text("{}", encoding="utf-8")

    assert classify_asset(image) == "image"
    assert classify_asset(scene) == "scene"
    assert classify_asset(prefab) == "prefab"
    assert classify_asset(tmp_path) == "folder"


def test_browser_directories_sort_before_files(tmp_path: Path):
    (tmp_path / "z_folder").mkdir()
    (tmp_path / "a_folder").mkdir()
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "b.wav").write_bytes(b"x")

    model = AssetBrowserModel(tmp_path)

    assert [entry.name for entry in model.entries] == [
        "a_folder",
        "z_folder",
        "a.png",
        "b.wav",
    ]


def test_browser_navigation_is_root_constrained(tmp_path: Path):
    child = tmp_path / "assets"
    child.mkdir()

    model = AssetBrowserModel(tmp_path)
    model.navigate(child)

    assert model.current_path == child.resolve()
    assert model.can_go_up is True

    model.go_up()

    assert model.current_path == tmp_path.resolve()
    assert model.can_go_up is False

    with pytest.raises(ValueError):
        model.navigate(tmp_path.parent)


def test_search_filters_current_directory(tmp_path: Path):
    (tmp_path / "player.png").write_bytes(b"x")
    (tmp_path / "enemy.png").write_bytes(b"x")
    (tmp_path / "player.wav").write_bytes(b"x")

    model = AssetBrowserModel(tmp_path)
    model.set_search("player")

    assert [entry.name for entry in model.entries] == [
        "player.png",
        "player.wav",
    ]


def test_ignored_editor_directories(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".venv").mkdir()
    (tmp_path / "assets").mkdir()

    model = AssetBrowserModel(tmp_path)

    assert [entry.name for entry in model.entries] == [
        "assets",
    ]


def test_drag_payload_is_project_relative(tmp_path: Path):
    assets = tmp_path / "assets"
    assets.mkdir()

    image = assets / "hero.png"
    image.write_bytes(b"x")

    model = AssetBrowserModel(tmp_path)
    model.navigate(assets)

    entry = model.entries[0]
    payload = entry.drag_payload

    assert payload.path == image.resolve()
    assert payload.relative_path == Path("assets/hero.png")
    assert payload.kind == "image"


def test_format_file_size():
    assert format_file_size(12) == "12 B"
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(1024 * 1024) == "1.0 MB"
