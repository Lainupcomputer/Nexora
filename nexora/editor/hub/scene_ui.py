from __future__ import annotations

from nexora.editor.hub.project_wizard import NewProjectWizard
from nexora.editor.theme import (
    ACCENT,
    BUTTON_BACKGROUND,
    BUTTON_HOVER,
    BUTTON_PRESSED,
    EDITOR_BACKGROUND,
    PANEL_BACKGROUND,
    PANEL_BACKGROUND_DARK,
    PANEL_BORDER,
    TOOLBAR_BACKGROUND,
)
from nexora.nodes import Button, FileDialog, Label, ListView, Panel


class HubSceneUIMixin:
    """Build and style the Project Hub UI."""

    def _build_ui(self) -> None:
        root = self.ui

        self.background = root.create_child("Background", node_type=Panel)
        self.background.background = EDITOR_BACKGROUND

        self.header = root.create_child("Header", node_type=Panel)
        self.header.background = TOOLBAR_BACKGROUND
        self.header.border_color = PANEL_BORDER
        self.header.border_width = 1.0

        self.title = self._label(self.header, "Title", "Nexora", 1.18)
        self.title.anchor = (0.0, 0.5)
        self.title.pivot = (0.0, 0.5)

        self.subtitle = self._label(
            self.header,
            "Subtitle",
            "Project Hub",
            0.62,
        )
        self.subtitle.anchor = (0.0, 0.5)
        self.subtitle.pivot = (0.0, 0.5)

        self.header_hint = self._label(
            self.header,
            "HeaderHint",
            "Open a project or launch an editor tool",
            0.56,
        )
        self.header_hint.anchor = (1.0, 0.5)
        self.header_hint.pivot = (1.0, 0.5)

        self.project_panel = root.create_child("ProjectPanel", node_type=Panel)
        self._style_panel(self.project_panel)

        self.project_title = self._section_title(self.project_panel, "Project")
        self.project_name = self._label(
            self.project_panel,
            "ProjectName",
            self.project_path.name,
            0.84,
        )
        self.project_name.anchor = (0.0, 0.0)
        self.project_name.pivot = (0.0, 0.0)

        self.project_path_label = self._label(
            self.project_panel,
            "ProjectPath",
            str(self.project_path),
            0.50,
        )
        self.project_path_label.anchor = (0.0, 0.0)
        self.project_path_label.pivot = (0.0, 0.0)

        self.new_project_button = self._button(
            self.project_panel,
            "NewProject",
            "New Project",
        )
        self.new_project_button.on_click = self._open_new_project_wizard

        self.open_project_button = self._button(
            self.project_panel,
            "OpenProject",
            "Open Project",
        )
        self.open_project_button.on_click = self._open_project_dialog

        self.recent_title = self._section_title(self.project_panel, "Recent Projects")
        self.recent_list = self.project_panel.create_child(
            "RecentProjects",
            node_type=ListView,
        )
        self.recent_list.item_height = 42.0
        self.recent_list.spacing = 3.0
        self.recent_list.padding_left = 5.0
        self.recent_list.padding_right = 5.0
        self.recent_list.padding_top = 5.0
        self.recent_list.padding_bottom = 5.0
        self.recent_list.text_padding_left = 10.0
        self.recent_list.text_scale = 0.58
        self.recent_list.on_change = self._on_recent_selected
        self.recent_list.on_activate = self._on_recent_activated

        self.recent_hint = self._label(
            self.project_panel,
            "RecentHint",
            "Double-click a project to switch",
            0.46,
        )
        self.recent_hint.anchor = (0.0, 1.0)
        self.recent_hint.pivot = (0.0, 1.0)

        self.recent_open_button = self._button(
            self.project_panel,
            "RecentOpen",
            "Open Selected",
        )
        self.recent_open_button.on_click = self._open_selected_recent

        self.recent_remove_button = self._button(
            self.project_panel,
            "RecentRemove",
            "Remove",
        )
        self.recent_remove_button.on_click = self._remove_selected_recent

        self.tools_panel = root.create_child("ToolsPanel", node_type=Panel)
        self._style_panel(self.tools_panel)

        self.tools_title = self._section_title(self.tools_panel, "Main Editor & Tools")
        self.tools_subtitle = self._label(
            self.tools_panel,
            "ToolsSubtitle",
            "Open the main workspace or a specialized editor",
            0.54,
        )
        self.tools_subtitle.anchor = (0.0, 0.0)
        self.tools_subtitle.pivot = (0.0, 0.0)

        self.scene_button = self._tool_button(
            "SceneEditor",
            "Nexora Main Editor",
            "Assemble scenes, nodes, prefabs and game assets",
            "--editor",
        )
        self.scene_button.border_color = ACCENT
        self.scene_button.border_width = 2.0
        self.tilemap_button = self._tool_button(
            "TileMapEditor",
            "TileMap Editor",
            "Create and edit tile maps",
            "--tilemapedit",
        )
        self.item_button = self._tool_button(
            "ItemEditor",
            "Item Editor",
            "Create game item data",
            "--itemedit",
        )
        self.cutscene_button = self._tool_button(
            "CutsceneEditor",
            "Cutscene Editor",
            "Build timeline-based cutscenes",
            "--cutsceneedit",
        )
        self.audio_button = self._tool_button(
            "AudioEditor",
            "Audio Editor",
            "Mix buses, effects and audio presets",
            "--audioedit",
        )

        self.footer = root.create_child("Footer", node_type=Panel)
        self.footer.background = TOOLBAR_BACKGROUND
        self.footer.border_color = PANEL_BORDER
        self.footer.border_width = 1.0

        self.status_label = self._label(self.footer, "Status", "Ready", 0.52)
        self.status_label.anchor = (0.0, 0.5)
        self.status_label.pivot = (0.0, 0.5)

        self.close_button = self._button(self.footer, "Close", "Close")
        self.close_button.on_click = self.game.stop

        self.project_dialog = root.create_child("ProjectDialog", node_type=FileDialog)
        self.project_dialog.allow_directories = True
        self.project_dialog.file_selected.connect(self._on_project_selected)

        self.new_project_wizard = root.create_child(
            "NewProjectWizard",
            node_type=NewProjectWizard,
        )
        self.new_project_wizard.on_browse = self._browse_new_project_location
        self.new_project_wizard.on_create_project = self._create_new_project

        self.new_project_location_dialog = root.create_child(
            "NewProjectLocationDialog",
            node_type=FileDialog,
        )
        self.new_project_location_dialog.allow_directories = True
        self.new_project_location_dialog.file_selected.connect(
            self._on_new_project_location_selected
        )

        self._refresh_recent_projects()
        self._sync_project_display()
        self._sync_layout(force=True)

    def _style_panel(self, panel: Panel) -> None:
        panel.background = PANEL_BACKGROUND
        panel.border_color = PANEL_BORDER
        panel.border_width = 1.0
        panel.border_radius = 7.0

    def _section_title(self, parent: Panel, text: str) -> Label:
        label = self._label(parent, f"{text.replace(' ', '')}Title", text, 0.72)
        label.anchor = (0.0, 0.0)
        label.pivot = (0.0, 0.0)
        return label

    @staticmethod
    def _label(parent: Panel, name: str, text: str, scale: float) -> Label:
        label = parent.create_child(name, node_type=Label)
        label.text = text
        label.scale = scale
        label.anchor = (0.5, 0.5)
        label.pivot = (0.5, 0.5)
        return label

    def _button(self, parent: Panel, name: str, text: str) -> Button:
        button = parent.create_child(name, node_type=Button)
        button.text = text
        button.text_scale = 0.68
        button.normal_background = BUTTON_BACKGROUND
        button.hover_background = BUTTON_HOVER
        button.pressed_background = BUTTON_PRESSED
        button.focus_background = BUTTON_HOVER
        button.focus_border_color = ACCENT
        return button

    def _tool_button(
        self,
        name: str,
        title: str,
        description: str,
        flag: str,
    ) -> Panel:
        card = self.tools_panel.create_child(f"{name}Card", node_type=Panel)
        card.background = PANEL_BACKGROUND_DARK
        card.border_color = PANEL_BORDER
        card.border_width = 1.0
        card.border_radius = 6.0

        title_label = self._label(card, f"{name}Title", title, 0.74)
        title_label.anchor = (0.0, 0.0)
        title_label.pivot = (0.0, 0.0)

        description_label = self._label(
            card,
            f"{name}Description",
            description,
            0.48,
        )
        description_label.anchor = (0.0, 0.0)
        description_label.pivot = (0.0, 0.0)

        button = self._button(card, f"{name}Open", "Open")
        button.on_click = lambda flag=flag: self._open_editor(flag)

        card._hub_title = title_label
        card._hub_description = description_label
        card._hub_button = button
        return card
