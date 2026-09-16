from __future__ import annotations

from pathlib import Path

from nexora import Game

from nexora.editor.scene import (
    EditorScene,
)
from nexora.editor.model import (
    EditorDocument,
    ProjectModel,
    SelectionService,
)


def resolve_project_path(
    project_path: str | Path | None,
) -> Path:
    """
    Resolve the project directory opened by the editor.

    ``None`` and ``"."`` both resolve to the current working
    directory. The path must exist and be a directory.
    """

    raw = (
        Path.cwd()
        if project_path is None
        else Path(
            project_path
        ).expanduser()
    )

    resolved = raw.resolve()

    if not resolved.exists():
        raise FileNotFoundError(
            f"Editor project path does not exist: "
            f"{resolved}"
        )

    if not resolved.is_dir():
        raise NotADirectoryError(
            f"Editor project path is not a directory: "
            f"{resolved}"
        )

    return resolved


class EditorApp(Game):
    """
    Nexora Editor application.

    The editor intentionally runs on Nexora itself. That keeps the
    editor on the same rendering, input, UI and scene stack as games
    built with the engine.
    """

    def __init__(
        self,
        *,
        project_path: str | Path | None = None,
    ) -> None:
        self.editor_project_path = (
            resolve_project_path(
                project_path
            )
        )

        super().__init__(
            project_name="NexoraEditor",
            title=(
                "Nexora Editor - "
                f"{self.editor_project_path.name}"
            ),
            width=1440,
            height=900,
            resizable=True,
        )

    def initialize(
        self,
    ) -> None:
        self.editor_project = ProjectModel(
            self.editor_project_path
        )

        self.editor_document = EditorDocument()
        self.editor_selection = SelectionService()

        self.scene = EditorScene(
            self,
            self.editor_project_path,
            project=self.editor_project,
            document=self.editor_document,
            selection=self.editor_selection,
        )


def run_editor(
    project_path: str | Path | None = None,
) -> int:
    try:
        app = EditorApp(
            project_path=project_path,
        )

    except (
        FileNotFoundError,
        NotADirectoryError,
    ) as exc:
        print(
            f"[Nexora Editor] {exc}"
        )

        return 2

    app.run()
    return 0
