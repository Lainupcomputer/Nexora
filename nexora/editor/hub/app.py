from __future__ import annotations

from pathlib import Path

from nexora import Game
from nexora.editor.hub.launch import HubLaunchMixin
from nexora.editor.hub.layout import HubLayoutMixin
from nexora.editor.hub.projects import HubProjectsMixin
from nexora.editor.hub.scene_ui import HubSceneUIMixin
from nexora.editor.main.app import resolve_project_path
from nexora.editor.model import EditorProjectContext
from nexora.scene import Scene


class EditorToolsScene(
    HubSceneUIMixin,
    HubProjectsMixin,
    HubLaunchMixin,
    HubLayoutMixin,
    Scene,
):
    """Main project hub and launcher for Nexora editor applications."""

    OUTER_MARGIN = 28.0
    HEADER_HEIGHT = 92.0
    FOOTER_HEIGHT = 54.0
    COLUMN_GAP = 18.0
    LEFT_WIDTH = 360.0

    def __init__(
            self,
            game,
            project_path: Path,
            project_context: EditorProjectContext | None = None,
        ) -> None:
            super().__init__("NexoraEditorTools")
            self.game = game
            self.project_context = project_context or EditorProjectContext.from_path(project_path)
            self.project_path = self.project_context.root
            self._last_viewport = (-1.0, -1.0)
            self._recent_projects: list[Path] = []
            self._recent_entries: list[Path] = []
            self._recent_selected_index = -1
            self._build_ui()
            self._remember_current_project()

    def update(self, delta_time: float) -> None:
            self._sync_layout()
            super().update(delta_time)


class EditorToolsApp(Game):
    """Bootstrap application for Nexora's project hub and editor tools."""

    def __init__(self, *, project_path: str | Path | None = None) -> None:
        self.editor_tools_project_path = resolve_project_path(project_path)
        self.editor_tools_project_context = EditorProjectContext.from_path(
            self.editor_tools_project_path
        )
        super().__init__(
            project_name="NexoraEditorTools",
            title=f"Nexora Project Hub - {self.editor_tools_project_path.name}",
            width=1080,
            height=720,
            resizable=True,
            editor_mode=True,
        )
        self.editor_tools_scene: EditorToolsScene | None = None

    def initialize(self) -> None:
        # The Project Hub is a launcher, not a game runtime.
        # Keep F3 and Shift+F3 from opening the global debug/audio overlays.
        if self.engine is not None:
            self.engine.debug_overlay_shortcuts_enabled = False

            debug_overlay = getattr(
                self.engine,
                "debug_overlay",
                None,
            )
            if debug_overlay is not None:
                debug_overlay.hide()
                debug_overlay.hide_audio()

        icon_path = self.editor_tools_project_context.icon_path
        if self.window is not None and icon_path.is_file():
            try:
                self.window.set_icon(icon_path)
            except Exception:
                pass

        self.editor_tools_scene = EditorToolsScene(
            self,
            self.editor_tools_project_path,
            self.editor_tools_project_context,
        )
        self.scene = self.editor_tools_scene


def run_editor_tools(project_path: str | Path | None = None) -> int:
    try:
        EditorToolsApp(project_path=project_path).run()
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"[Nexora Editor Tools] {exc}")
        return 2
    return 0


__all__ = ["EditorToolsApp", "EditorToolsScene", "run_editor_tools"]
