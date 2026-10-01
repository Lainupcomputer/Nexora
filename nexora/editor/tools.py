from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from nexora import Game
from nexora.editor.app import resolve_project_path
from nexora.editor.model import EditorProjectContext
from nexora.editor.theme import (
    ACCENT,
    BUTTON_BACKGROUND,
    BUTTON_HOVER,
    BUTTON_PRESSED,
    EDITOR_BACKGROUND,
    PANEL_BACKGROUND,
    PANEL_BORDER,
)
from nexora.nodes import Button, FileDialog, Label, Panel
from nexora.scene import Scene


class EditorToolsScene(Scene):
    """Small launcher window for Nexora's standalone editor tools."""

    CARD_WIDTH = 560.0
    CARD_HEIGHT = 520.0

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
        self._build_ui()

    def _build_ui(self) -> None:
        root = self.ui

        self.background = root.create_child("Background", node_type=Panel)
        self.background.background = EDITOR_BACKGROUND

        self.card = root.create_child("ToolsCard", node_type=Panel)
        self.card.background = PANEL_BACKGROUND
        self.card.border_color = PANEL_BORDER
        self.card.border_width = 1.0
        self.card.border_radius = 8.0

        self.title = self._label(self.card, "Title", "Nexora Editor Tools", 1.05)
        self.subtitle = self._label(
            self.card,
            "Subtitle",
            "Choose an editor for this project",
            0.66,
        )
        self.project_label = self._label(
            self.card,
            "Project",
            f"Project: {self.project_path}",
            0.56,
        )
        self.change_project_button = self._button(
            self.card,
            "ChangeProject",
            "Change Project",
            None,
        )
        self.change_project_button.on_click = self._open_project_dialog

        self.scene_button = self._button(
            self.card, "SceneEditor", "Scene Editor", "--editor"
        )
        self.tilemap_button = self._button(
            self.card, "TileMapEditor", "TileMap Editor", "--tilemapedit"
        )
        self.item_button = self._button(
            self.card, "ItemEditor", "Item Editor", "--itemedit"
        )
        self.cutscene_button = self._button(
            self.card, "CutsceneEditor", "Cutscene Editor", "--cutsceneedit"
        )

        self.status_label = self._label(self.card, "Status", "Ready", 0.54)
        self.close_button = self._button(self.card, "Close", "Close", None)
        self.close_button.on_click = self.game.stop

        self.project_dialog = root.create_child(
            "ProjectDialog",
            node_type=FileDialog,
        )
        self.project_dialog.allow_directories = True
        self.project_dialog.file_selected.connect(
            self._on_project_selected
        )

        self._sync_layout()

    def _open_project_dialog(self) -> None:
        home = Path.home().resolve()
        current = self.project_path
        try:
            current.relative_to(home)
        except ValueError:
            current = home

        self.project_dialog.configure(
            mode="open",
            root_path=home,
            current_path=current,
            title="Choose Project Folder",
        )
        self.project_dialog.allow_directories = True
        self.project_dialog.confirm_text = "Select Project"
        self.project_dialog.open()

    def _on_project_selected(self, _dialog, path: Path) -> None:
        try:
            self.project_path = resolve_project_path(path)
        except (FileNotFoundError, NotADirectoryError) as exc:
            self.status_label.text = str(exc)
            return

        self.project_label.text = f"Project: {self.project_path}"
        self.status_label.text = f"Project selected: {self.project_path.name}"

    @staticmethod
    def _label(parent: Panel, name: str, text: str, scale: float) -> Label:
        label = parent.create_child(name, node_type=Label)
        label.text = text
        label.scale = scale
        label.anchor = (0.5, 0.5)
        label.pivot = (0.5, 0.5)
        return label

    def _button(
        self,
        parent: Panel,
        name: str,
        text: str,
        flag: str | None,
    ) -> Button:
        button = parent.create_child(name, node_type=Button)
        button.text = text
        button.text_scale = 0.78
        button.normal_background = BUTTON_BACKGROUND
        button.hover_background = BUTTON_HOVER
        button.pressed_background = BUTTON_PRESSED
        button.focus_background = BUTTON_HOVER
        button.focus_border_color = ACCENT
        if flag is not None:
            button.on_click = lambda flag=flag: self._open_editor(flag)
        return button

    def _open_editor(self, flag: str) -> None:
        command = [
            sys.executable,
            "-m",
            "nexora",
            flag,
            str(self.project_path),
        ]

        try:
            subprocess.Popen(command, cwd=str(self.project_path))
        except OSError as exc:
            self.status_label.text = f"Could not start editor: {exc}"
            return

        names = {
            "--editor": "Scene Editor",
            "--tilemapedit": "TileMap Editor",
            "--itemedit": "Item Editor",
            "--cutsceneedit": "Cutscene Editor",
        }
        self.status_label.text = f"Started {names.get(flag, flag)}"

    def _sync_layout(self) -> None:
        renderer = getattr(self.game, "renderer", None)
        if renderer is None:
            return

        width = float(renderer.width)
        height = float(renderer.height)
        if (width, height) == self._last_viewport:
            return
        self._last_viewport = (width, height)

        self.background.size = (width, height)
        self.background.position = (0.0, 0.0)
        self.background.anchor = (0.5, 0.5)
        self.background.pivot = (0.5, 0.5)

        self.card.size = (self.CARD_WIDTH, self.CARD_HEIGHT)
        self.card.position = (0.0, 0.0)
        self.card.anchor = (0.5, 0.5)
        self.card.pivot = (0.5, 0.5)

        self.title.position = (0.0, -190.0)
        self.subtitle.position = (0.0, -155.0)
        self.project_label.position = (0.0, -120.0)
        self.change_project_button.size = (190.0, 42.0)
        self.change_project_button.position = (0.0, -78.0)
        self.change_project_button.anchor = (0.5, 0.5)
        self.change_project_button.pivot = (0.5, 0.5)

        for button, y in (
            (self.scene_button, -25.0),
            (self.tilemap_button, 39.0),
            (self.item_button, 103.0),
            (self.cutscene_button, 167.0),
        ):
            button.size = (390.0, 48.0)
            button.position = (0.0, y)
            button.anchor = (0.5, 0.5)
            button.pivot = (0.5, 0.5)

        self.status_label.position = (0.0, 195.0)
        self.close_button.size = (150.0, 42.0)
        self.close_button.position = (0.0, 225.0)
        self.close_button.anchor = (0.5, 0.5)
        self.close_button.pivot = (0.5, 0.5)

    def update(self, delta_time: float) -> None:
        self._sync_layout()
        super().update(delta_time)


class EditorToolsApp(Game):
    """Bootstrap application that launches Nexora editor tools."""

    def __init__(self, *, project_path: str | Path | None = None) -> None:
        self.editor_tools_project_path = resolve_project_path(project_path)
        self.editor_tools_project_context = EditorProjectContext.from_path(
            self.editor_tools_project_path
        )
        super().__init__(
            project_name="NexoraEditorTools",
            title=f"Nexora Editor Tools - {self.editor_tools_project_path.name}",
            width=720,
            height=580,
            resizable=False,
            editor_mode=True,
        )
        self.editor_tools_scene: EditorToolsScene | None = None

    def initialize(self) -> None:
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
