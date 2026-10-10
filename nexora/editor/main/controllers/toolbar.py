from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING, Callable

from nexora.nodes import Button, Label, Panel
from nexora.editor.theme import (
    ACCENT,
    PANEL_BACKGROUND_DARK,
    PANEL_BORDER,
    TOOLBAR_BACKGROUND,
)

if TYPE_CHECKING:
    from nexora.editor.main.scene import EditorScene


class ToolbarController:
    """Owns the editor toolbar, menus, play controls, and tool launching."""

    def __init__(self, scene: "EditorScene") -> None:
        self.scene = scene

    def build_toolbar(self) -> None:
        scene = self.scene
        scene.brand_label = scene.toolbar.create_child("Brand", node_type=Label)
        scene.brand_label.text = "NEXORA"
        scene.brand_label.scale = 0.9
        scene.brand_label.anchor = (0.0, 0.5)
        scene.brand_label.pivot = (0.0, 0.5)

        scene.file_menu_button = self.toolbar_menu_button("FileMenu", "File", "file")
        scene.edit_menu_button = self.toolbar_menu_button("EditMenu", "Edit", "edit")
        scene.scene_menu_button = self.toolbar_menu_button("SceneMenu", "Scene", "scene")
        scene.tools_menu_button = self.toolbar_menu_button("ToolsMenu", "Tools", "tools")
        scene.run_menu_button = self.toolbar_menu_button("RunMenu", "Run", "run")

        scene.play_button = scene._button(
            scene.toolbar,
            "PlayButton",
            "▶ Run",
            scene._toggle_play_mode,
        )
        scene.play_button.text_scale = 0.70
        scene.play_button.focus_border_color = ACCENT

        scene.document_label = scene.toolbar.create_child(
            "DocumentLabel",
            node_type=Label,
        )
        scene.document_label.scale = 0.72
        scene.document_label.anchor = (1.0, 0.5)
        scene.document_label.pivot = (1.0, 0.5)

    def toolbar_menu_button(self, name: str, text: str, menu_name: str) -> Button:
        scene = self.scene
        button = scene._button(
            scene.toolbar,
            name,
            text,
            lambda menu_name=menu_name: scene._toggle_toolbar_menu(menu_name),
        )
        button.normal_background = TOOLBAR_BACKGROUND
        button.text_scale = 0.70
        return button

    def build_toolbar_menus(self) -> None:
        scene = self.scene
        scene._toolbar_menu_panels = {}
        scene._toolbar_menu_items = {}
        scene._active_toolbar_menu = None

        definitions = {
            "file": (
                ("New Scene", scene.document_controller.request_new_scene),
                ("Open Scene", scene.document_controller.request_open_scene),
                ("Save", scene.document_controller.save_scene),
                ("Save As...", scene.document_controller.save_scene_as),
                ("Save as Prefab", scene.document_controller.save_selected_prefab),
                ("Exit", scene.game.stop),
            ),
            "edit": (
                ("Undo", scene.scene_tree_controller.undo),
                ("Redo", scene.scene_tree_controller.redo),
            ),
            "scene": (
                ("Add Node...", scene.scene_tree_controller.open_add_node_dialog),
                ("Rename Node...", scene.scene_tree_controller.open_rename_node_dialog),
                ("Delete Node", scene.scene_tree_controller.request_delete_node),
            ),
            "tools": (
                ("TileMap Editor", scene._open_tilemap_editor),
                ("Item Editor", lambda: scene._open_editor_tool("--itemedit", "Item Editor")),
                ("Cutscene Editor", lambda: scene._open_editor_tool("--cutsceneedit", "Cutscene Editor")),
                ("Audio Editor", lambda: scene._open_editor_tool("--audioedit", "Audio Editor")),
                ("Project Hub", lambda: scene._open_editor_tool("--editor-tools", "Project Hub")),
            ),
            "run": (
                ("Run Project", scene._start_play_mode),
                ("Stop Project", scene._stop_play_mode),
            ),
        }

        for menu_name, entries in definitions.items():
            panel = scene.ui.create_child(
                f"ToolbarMenu{menu_name.title()}",
                node_type=Panel,
            )
            panel.background = PANEL_BACKGROUND_DARK
            panel.border_color = PANEL_BORDER
            panel.border_width = 1.0
            panel.visible = False
            scene._toolbar_menu_panels[menu_name] = panel

            buttons: list[Button] = []
            for index, (label, callback) in enumerate(entries):
                button = scene._button(
                    panel,
                    f"ToolbarMenu{menu_name.title()}Item{index}",
                    label,
                    lambda callback=callback: scene._run_toolbar_menu_action(callback),
                )
                button.text_scale = 0.66
                button.normal_background = PANEL_BACKGROUND_DARK
                buttons.append(button)
            scene._toolbar_menu_items[menu_name] = buttons

    def toggle_toolbar_menu(self, menu_name: str) -> None:
        scene = self.scene
        target = scene._toolbar_menu_panels.get(menu_name)
        if target is None:
            return

        opening = not target.visible
        self.close_toolbar_menus()
        if opening:
            target.visible = True
            scene._active_toolbar_menu = menu_name

    def close_toolbar_menus(self) -> None:
        scene = self.scene
        for panel in scene._toolbar_menu_panels.values():
            panel.visible = False
        scene._active_toolbar_menu = None

    def run_toolbar_menu_action(self, callback: Callable[[], None]) -> None:
        self.close_toolbar_menus()
        callback()

    def toggle_play_mode(self) -> None:
        if self.scene.game.play_mode:
            self.stop_play_mode()
        else:
            self.start_play_mode()

    def start_play_mode(self) -> None:
        scene = self.scene
        if not scene.game.play_mode:
            scene.game.start_play_mode()
        self.sync_play_button()

    def stop_play_mode(self) -> None:
        scene = self.scene
        if scene.game.play_mode:
            scene.game.stop_play_mode()
        self.sync_play_button()

    def sync_play_button(self) -> None:
        scene = self.scene
        if not hasattr(scene, "play_button"):
            return
        scene.play_button.text = "■ Stop" if scene.game.play_mode else "▶ Run"

    def open_editor_tool(self, flag: str, display_name: str) -> None:
        scene = self.scene
        command = [
            sys.executable,
            "-m",
            "nexora",
            flag,
            str(scene.project_path),
        ]
        try:
            subprocess.Popen(command, cwd=str(scene.project_path))
            scene.status_label.text = f"Started {display_name}"
        except OSError as exc:
            scene._show_error(f"Could not start {display_name}:\n{exc}")

    def open_tilemap_editor(self) -> None:
        scene = self.scene
        command = [
            sys.executable,
            "-m",
            "nexora",
            "--tilemapedit",
            str(scene.project_path),
        ]
        selected = scene.selection.selected
        tilemap_asset = getattr(selected, "tilemap_asset", None)
        if tilemap_asset:
            command.extend(("--tilemap", str(tilemap_asset)))

        try:
            subprocess.Popen(command, cwd=str(scene.project_path))
            scene.status_label.text = "Started TileMap Editor"
        except OSError as exc:
            scene._show_error(f"Could not start TileMap Editor:\n{exc}")

    def sync_layout(self, width: float) -> None:
        scene = self.scene
        scene.brand_label.position = (16.0, 0.0)

        menu_buttons = (
            (scene.file_menu_button, 54.0),
            (scene.edit_menu_button, 54.0),
            (scene.scene_menu_button, 64.0),
            (scene.tools_menu_button, 62.0),
            (scene.run_menu_button, 54.0),
        )
        x = 104.0
        gap = 2.0
        menu_left_edges: dict[str, float] = {}
        for menu_name, (button, button_width) in zip(
            ("file", "edit", "scene", "tools", "run"),
            menu_buttons,
        ):
            button.size = (button_width, 34.0)
            button.anchor = (0.0, 0.5)
            button.pivot = (0.5, 0.5)
            button.position = (x + button_width / 2.0, 0.0)
            menu_left_edges[menu_name] = x
            x += button_width + gap

        scene.play_button.size = (86.0, 34.0)
        scene.play_button.anchor = (0.0, 0.5)
        scene.play_button.pivot = (0.5, 0.5)
        scene.play_button.position = (x + 49.0, 0.0)

        menu_widths = {
            "file": 190.0,
            "edit": 140.0,
            "scene": 180.0,
            "tools": 210.0,
            "run": 160.0,
        }
        item_height = 32.0
        for menu_name, panel in scene._toolbar_menu_panels.items():
            buttons = scene._toolbar_menu_items[menu_name]
            panel_width = menu_widths[menu_name]
            panel_height = max(item_height, len(buttons) * item_height + 8.0)
            panel.anchor = (0.0, 0.0)
            panel.pivot = (0.5, 0.5)
            panel.size = (panel_width, panel_height)
            panel.position = (
                menu_left_edges[menu_name] + panel_width / 2.0,
                scene.TOOLBAR_HEIGHT + panel_height / 2.0,
            )

            for index, button in enumerate(buttons):
                button.anchor = (0.5, 0.0)
                button.pivot = (0.5, 0.5)
                button.size = (panel_width - 8.0, item_height - 2.0)
                button.position = (0.0, 5.0 + item_height * index + item_height / 2.0)

        scene.document_label.position = (-16.0, 0.0)
