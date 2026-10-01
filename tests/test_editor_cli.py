from __future__ import annotations

from pathlib import Path

import pytest

from nexora.cli.main import build_parser
from nexora.editor.app import resolve_project_path


def test_cli_editor_defaults_to_current_directory() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["--editor"]
    )

    assert args.editor == "."
    assert args.command is None


def test_cli_editor_accepts_project_path() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--editor",
            "MyGame",
        ]
    )

    assert args.editor == "MyGame"
    assert args.command is None


def test_cli_editor_tools_defaults_to_current_directory() -> None:
    parser = build_parser()
    args = parser.parse_args(["--editor-tools"])

    assert args.editor_tools == "."
    assert args.command is None


def test_cli_editor_tools_accepts_project_path() -> None:
    parser = build_parser()
    args = parser.parse_args(["--editor-tools", "MyProject"])

    assert args.editor_tools == "MyProject"
    assert args.command is None


def test_cli_tilemap_editor_defaults_to_current_directory() -> None:
    parser = build_parser()
    args = parser.parse_args(["--tilemapedit"])

    assert args.tilemapedit == "."
    assert args.scene is None
    assert args.command is None


def test_cli_tilemap_editor_accepts_project_and_scene() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--tilemapedit",
            "MyProject",
            "--scene",
            "scenes/world.nxscene",
        ]
    )

    assert args.tilemapedit == "MyProject"
    assert args.scene == "scenes/world.nxscene"
    assert args.command is None


def test_cli_item_editor_accepts_project_and_item() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--itemedit",
            "MyProject",
            "--item",
            "items/iron_sword.nitem",
        ]
    )

    assert args.itemedit == "MyProject"
    assert args.item == "items/iron_sword.nitem"
    assert args.command is None


def test_cli_cutscene_editor_accepts_project_and_asset() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--cutscene-editor",
            "MyProject",
            "--cutscene",
            "cutscenes/intro.ncutscene",
        ]
    )

    assert args.cutsceneedit == "MyProject"
    assert args.cutscene == "cutscenes/intro.ncutscene"
    assert args.command is None


def test_cli_create_still_works() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "create",
            "MyGame",
            "--path",
            "projects",
        ]
    )

    assert args.command == "create"
    assert args.name == "MyGame"
    assert args.path == "projects"


def test_resolve_project_path(
    tmp_path: Path,
) -> None:
    resolved = resolve_project_path(
        tmp_path
    )

    assert resolved == (
        tmp_path.resolve()
    )


def test_resolve_project_path_rejects_missing(
    tmp_path: Path,
) -> None:
    missing = (
        tmp_path
        / "missing"
    )

    with pytest.raises(
        FileNotFoundError
    ):
        resolve_project_path(
            missing
        )


def test_resolve_project_path_rejects_file(
    tmp_path: Path,
) -> None:
    file_path = (
        tmp_path
        / "project.txt"
    )

    file_path.write_text(
        "not a directory",
        encoding="utf-8",
    )

    with pytest.raises(
        NotADirectoryError
    ):
        resolve_project_path(
            file_path
        )


def test_cli_audio_editor_defaults_to_current_directory() -> None:
    parser = build_parser()
    args = parser.parse_args(["--audioedit"])

    assert args.audioedit == "."
    assert args.command is None


def test_cli_audio_editor_accepts_project_path() -> None:
    parser = build_parser()
    args = parser.parse_args(["--audioedit", "MyProject"])

    assert args.audioedit == "MyProject"
    assert args.command is None
