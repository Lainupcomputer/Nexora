from __future__ import annotations

from pathlib import Path

from nexora.core.paths import (
    ProjectPaths,
)


def test_project_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        Path,
        "home",
        classmethod(
            lambda cls: tmp_path
        ),
    )

    paths = (
        ProjectPaths(
            "MyGame"
        )
    )

    assert (
        paths.root
        == (
            tmp_path
            / "Documents"
            / "MyGame"
        )
    )

    assert (
        paths.settings
        == (
            tmp_path
            / "Documents"
            / "MyGame"
            / "settings"
        )
    )

    assert (
        paths.saves
        == (
            tmp_path
            / "Documents"
            / "MyGame"
            / "saves"
        )
    )


def test_project_paths_ensure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        Path,
        "home",
        classmethod(
            lambda cls: tmp_path
        ),
    )

    paths = (
        ProjectPaths(
            "MyGame"
        )
    )

    paths.ensure()

    assert (
        paths.settings.is_dir()
    )

    assert (
        paths.saves.is_dir()
    )


def test_save_file_helper(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        Path,
        "home",
        classmethod(
            lambda cls: tmp_path
        ),
    )

    paths = (
        ProjectPaths(
            "MyGame"
        )
    )

    assert (
        paths.save_file(
            "quicksave.nsave"
        )
        == (
            paths.saves
            / "quicksave.nsave"
        )
    )