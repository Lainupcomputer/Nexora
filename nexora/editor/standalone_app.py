from __future__ import annotations

"""Shared bootstrap for Nexora standalone editor applications."""

from pathlib import Path
from typing import Any, Generic, TypeVar

from nexora import Game
from nexora.editor.main.app import resolve_project_path
from nexora.editor.model import EditorProjectContext


SceneT = TypeVar("SceneT")


class StandaloneEditorApp(Game, Generic[SceneT]):
    """Common ``Game`` bootstrap used by all standalone editors.

    Concrete editors only provide their window metadata and create their
    domain-specific scene. Project resolution, editor-mode Game setup, asset
    root wiring, window icon setup and scene installation live here once.
    """

    PROJECT_NAME = "NexoraStandaloneEditor"
    WINDOW_TITLE = "Nexora Editor"
    WINDOW_WIDTH = 1440
    WINDOW_HEIGHT = 900
    ERROR_PREFIX = "Nexora Editor"

    def __init__(self, *, project_path: str | Path | None = None) -> None:
        self.project_path = resolve_project_path(project_path)
        self.project_context = EditorProjectContext.from_path(self.project_path)
        self.editor_scene: SceneT | None = None
        super().__init__(
            project_name=self.PROJECT_NAME,
            title=f"{self.WINDOW_TITLE} - {self.project_path.name}",
            width=self.WINDOW_WIDTH,
            height=self.WINDOW_HEIGHT,
            resizable=True,
            editor_mode=True,
        )

    def editor_asset_reference(self) -> str | Path | None:
        """Reference used to select this editor application's asset root."""
        return None

    def editor_asset_root(self) -> Path:
        """Return the asset root to expose through the engine asset manager."""
        return self.project_context.asset_root_for(self.editor_asset_reference())

    def editor_icon_path(self) -> Path:
        """Return the icon used by this editor window."""
        return self.editor_asset_root() / "icon.png"

    def create_editor_scene(self) -> SceneT:
        """Create the concrete editor scene."""
        raise NotImplementedError

    def after_editor_scene_created(self, scene: SceneT) -> None:
        """Hook for editor-specific initial file loading or setup."""
        del scene

    def initialize(self) -> None:
        if self.engine is not None:
            self.engine.assets.root = self.editor_asset_root()

        icon_path = self.editor_icon_path()
        if self.window is not None and icon_path.is_file():
            try:
                self.window.set_icon(icon_path)
            except Exception:
                # A window icon is cosmetic and must never prevent an editor
                # from starting on a platform/backend that rejects the image.
                pass

        scene = self.create_editor_scene()
        self.editor_scene = scene
        self.scene = scene
        self.after_editor_scene_created(scene)


def run_standalone_editor(app_type: type[StandaloneEditorApp[Any]], /, **kwargs: Any) -> int:
    """Run one standalone editor with the shared project-path error contract."""
    try:
        app_type(**kwargs).run()
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"[{app_type.ERROR_PREFIX}] {exc}")
        return 2
    return 0


__all__ = ["StandaloneEditorApp", "run_standalone_editor"]
