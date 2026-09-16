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
