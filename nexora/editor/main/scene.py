from __future__ import annotations

from pathlib import Path

from nexora.nodes import Label, Panel
from nexora.editor.base_editor import EditorBaseScene

from nexora.editor.model import (
    EditorDocument,
    EditorProjectContext,
    ProjectModel,
    SelectionService,
)

from nexora.editor.main.controllers import (
    AnimationPanelController,
    AssetBrowserController,
    BottomDockController,
    DocumentController,
    InspectorController,
    SceneTreeController,
    ViewportController,
    ToolbarController,
    WorkspaceController,
)

from nexora.editor.commands import CommandStack

from nexora.editor.main.viewport import (
    EditorViewportState,
    GIZMO_MOVE,
)

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
    VIEWPORT_BACKGROUND,
)


class EditorScene(EditorBaseScene):
    """Nexora Editor shell with scene document management."""

    TOOLBAR_HEIGHT = 48.0
    STATUS_HEIGHT = 26.0
    LEFT_WIDTH = 250.0
    RIGHT_WIDTH = 310.0
    BOTTOM_HEIGHT = 190.0
    GAP = 1.0

    def __init__(
        self,
        game,
        project_path: Path,
        *,
        project: ProjectModel,
        document: EditorDocument,
        selection: SelectionService,
        project_context: EditorProjectContext | None = None,
    ) -> None:
        super().__init__("NexoraEditor")

        self.game = game
        self.project_context = project_context or EditorProjectContext.from_path(project_path)
        self.project_path = self.project_context.root
        self.project = project
        self.document = document
        self.selection = selection
        self.commands = CommandStack()
        self._scene_entries = []
        self._last_size = (-1.0, -1.0)
        self.document_controller = DocumentController(self)
        self.scene_tree_controller = SceneTreeController(self)
        self.inspector_controller = InspectorController(self)
        self.viewport_controller = ViewportController(self)
        self.asset_browser_controller = AssetBrowserController(self)
        self.animation_controller = AnimationPanelController(self)
        self.bottom_dock_controller = BottomDockController(self)
        self.toolbar_controller = ToolbarController(self)
        self.workspace_controller = WorkspaceController(self)

        self.viewport_state = EditorViewportState()

        self.viewport_tool = GIZMO_MOVE
        self.viewport_snap_enabled = False
        self.viewport_move_snap = 32.0
        self.viewport_rotate_snap = 15.0
        self.viewport_scale_snap = 0.10

        self._gizmo_drag = None
        self._gizmo_active_handle = None

        self._bottom_tab = "assets"
        self._animation_clip_name = None

        self._build_ui()

    # ==========================================================
    # BUILD
    # ==========================================================

    def _build_ui(self) -> None:
        root = self.ui

        self.background = root.create_child("EditorBackground", node_type=Panel)
        self.background.background = EDITOR_BACKGROUND

        self.toolbar = root.create_child("Toolbar", node_type=Panel)
        self.toolbar.background = TOOLBAR_BACKGROUND
        self.toolbar.border_color = PANEL_BORDER
        self.toolbar.border_width = 1.0

        self.scene_tree = root.create_child("SceneTree", node_type=Panel)
        self._style_panel(self.scene_tree)

        self.viewport = root.create_child("Viewport", node_type=Panel)
        self.viewport.background = VIEWPORT_BACKGROUND
        self.viewport.border_color = PANEL_BORDER
        self.viewport.border_width = 1.0

        self.inspector = root.create_child("Inspector", node_type=Panel)
        self._style_panel(self.inspector)

        self.bottom_dock = root.create_child("BottomDock", node_type=Panel)
        self.bottom_dock.background = PANEL_BACKGROUND_DARK
        self.bottom_dock.border_color = PANEL_BORDER
        self.bottom_dock.border_width = 1.0

        self.status_bar = root.create_child("StatusBar", node_type=Panel)
        self.status_bar.background = TOOLBAR_BACKGROUND
        self.status_bar.border_color = PANEL_BORDER
        self.status_bar.border_width = 1.0

        self._build_toolbar()
        self._build_scene_tree()
        self._build_viewport()
        self._build_inspector()
        self._build_bottom_dock()
        self._build_status_bar()
        self._build_dialogs()
        self._build_asset_drag_overlay()
        self._build_toolbar_menus()

        self.selection.changed.connect(self._on_selection_changed)
        self._refresh_document_ui()

    def _style_panel(self, panel: Panel) -> None:
        panel.background = PANEL_BACKGROUND
        panel.border_color = PANEL_BORDER
        panel.border_width = 1.0

    def _get_toolbar_controller(self) -> ToolbarController:
        controller = getattr(self, "toolbar_controller", None)
        if controller is None:
            controller = ToolbarController(self)
            self.toolbar_controller = controller
        return controller

    def _get_document_controller(self) -> DocumentController:
        controller = getattr(self, "document_controller", None)
        if controller is None:
            controller = DocumentController(self)
            self.document_controller = controller
        return controller

    def _get_scene_tree_controller(self) -> SceneTreeController:
        controller = getattr(self, "scene_tree_controller", None)
        if controller is None:
            controller = SceneTreeController(self)
            self.scene_tree_controller = controller
        return controller

    def _get_inspector_controller(self) -> InspectorController:
        controller = getattr(self, "inspector_controller", None)
        if controller is None:
            controller = InspectorController(self)
            self.inspector_controller = controller
        return controller

    def _get_workspace_controller(self) -> WorkspaceController:
        controller = getattr(self, "workspace_controller", None)
        if controller is None:
            controller = WorkspaceController(self)
            self.workspace_controller = controller
        return controller

    # ==========================================================
    # TOOLBAR
    # ==========================================================

    def _build_toolbar(self) -> None:
        self._get_toolbar_controller().build_toolbar()


    def _build_toolbar_menus(self) -> None:
        self._get_toolbar_controller().build_toolbar_menus()


    def _toggle_toolbar_menu(self, menu_name: str) -> None:
        self._get_toolbar_controller().toggle_toolbar_menu(menu_name)


    def _run_toolbar_menu_action(self, callback) -> None:
        self._get_toolbar_controller().run_toolbar_menu_action(callback)


    # ==========================================================
    # WORKSPACE / DIALOGS
    # ==========================================================

    def _build_dialogs(self) -> None:
        self._get_workspace_controller().build_dialogs()

    def _serialization_context(self) -> dict:
        return self._get_workspace_controller().serialization_context()

    # ==========================================================
    # DOCUMENT WORKFLOW
    # ==========================================================

    def request_new_scene(self) -> None:
        """Compatibility forwarder to the document controller."""
        self._get_document_controller().request_new_scene()

    def request_open_scene(self) -> None:
        """Compatibility forwarder to the document controller."""
        self._get_document_controller().request_open_scene()

    def save_scene(self) -> None:
        """Compatibility forwarder to the document controller."""
        self._get_document_controller().save_scene()

    def save_scene_as(self) -> None:
        """Compatibility forwarder to the document controller."""
        self._get_document_controller().save_scene_as()

    def save_selected_prefab(self) -> None:
        """Compatibility forwarder to the document controller."""
        self._get_document_controller().save_selected_prefab()

    def _show_error(self, message: str) -> None:
        self._get_workspace_controller().show_error(message)

    # ==========================================================
    # SCENE TREE / NODE EDITING
    # ==========================================================

    def _build_scene_tree(self) -> None:
        self._get_scene_tree_controller().build_scene_tree()

    def _refresh_scene_tree(self) -> None:
        self._get_scene_tree_controller().refresh_scene_tree()

    def _editable_selected_node(self):
        return self._get_scene_tree_controller().editable_selected_node()

    def open_add_node_dialog(self) -> None:
        self._get_scene_tree_controller().open_add_node_dialog()

    def open_rename_node_dialog(self) -> None:
        self._get_scene_tree_controller().open_rename_node_dialog()

    def request_delete_node(self) -> None:
        self._get_scene_tree_controller().request_delete_node()

    def undo(self) -> None:
        self._get_scene_tree_controller().undo()

    def redo(self) -> None:
        self._get_scene_tree_controller().redo()

    def _sync_add_node_dialog_layout(self) -> None:
        self._get_scene_tree_controller().sync_add_node_dialog_layout()

    # ==========================================================
    # VIEWPORT
    # ==========================================================

    def _build_viewport(self) -> None:
        self._get_viewport_controller().build_viewport()

    def _selected_animation_player(self):
        return self._get_animation_controller()._selected_animation_player()

    def _animation_speed_property(self, node) -> str:
        return self._get_animation_controller()._animation_speed_property(node)

    def _animation_speed(self, node) -> float:
        return self._get_animation_controller()._animation_speed(node)

    def _add_animation_clip(self) -> None:
        self._get_animation_controller()._add_animation_clip()

    def _refresh_animation_panel(self) -> None:
        self._get_animation_controller()._refresh_animation_panel()

    def _on_animation_selected(self, index: int, _label: str | None) -> None:
        self._get_animation_controller()._on_animation_selected(index, _label)

    def _on_animation_speed_submitted(self, text: str) -> None:
        self._get_animation_controller()._on_animation_speed_submitted(text)

    def _play_selected_animation(self) -> None:
        self._get_animation_controller()._play_selected_animation()

    def _pause_selected_animation(self) -> None:
        self._get_animation_controller()._pause_selected_animation()

    def _stop_selected_animation(self) -> None:
        self._get_animation_controller()._stop_selected_animation()

    def _any_editor_dialog_open(self) -> bool:
        return self._get_workspace_controller().any_editor_dialog_open()

    def _get_asset_browser_controller(self) -> AssetBrowserController:
        controller = getattr(self, "asset_browser_controller", None)
        if controller is None:
            controller = AssetBrowserController(self)
            self.asset_browser_controller = controller
        return controller

    def _get_viewport_controller(self) -> ViewportController:
        controller = getattr(self, "viewport_controller", None)
        if controller is None:
            controller = ViewportController(self)
            self.viewport_controller = controller
        return controller

    def _get_animation_controller(self) -> AnimationPanelController:
        controller = getattr(self, "animation_controller", None)
        if controller is None:
            controller = AnimationPanelController(self)
            self.animation_controller = controller
        return controller

    def _get_bottom_dock_controller(self) -> BottomDockController:
        controller = getattr(self, "bottom_dock_controller", None)
        if controller is None:
            controller = BottomDockController(self)
            self.bottom_dock_controller = controller
        return controller

    def _viewport_mouse_centered(self) -> tuple[float, float]:
        return self._get_viewport_controller().viewport_mouse_centered()

    def _mouse_inside_viewport_canvas(self) -> bool:
        return self._get_viewport_controller().mouse_inside_viewport_canvas()

    def _iter_viewport_nodes(self):
        yield from self._get_viewport_controller().iter_viewport_nodes()

    def _select_node_from_viewport(self) -> None:
        self._get_viewport_controller().select_node_from_viewport()

    def _focus_selected_node(self) -> None:
        self._get_viewport_controller().focus_selected_node()

    def _selected_viewport_node(self):
        return self._get_viewport_controller().selected_viewport_node()

    @staticmethod
    def _snap_value(
        value: float,
        step: float,
    ) -> float:
        step = abs(
            float(step)
        )

        if step <= 1e-9:
            return float(
                value
            )

        return round(
            float(value) / step
        ) * step

    def _gizmo_pivot_screen(self, node) -> tuple[float, float]:
        return self._get_viewport_controller().gizmo_pivot_screen(node)

    def _begin_gizmo_drag(self, node, handle: str, mouse_x: float, mouse_y: float) -> None:
        self._get_viewport_controller().begin_gizmo_drag(node, handle, mouse_x, mouse_y)

    def _update_gizmo_drag(self, mouse_x: float, mouse_y: float) -> None:
        self._get_viewport_controller().update_gizmo_drag(mouse_x, mouse_y)

    def _finish_gizmo_drag(self, *, cancel: bool = False) -> None:
        self._get_viewport_controller().finish_gizmo_drag(cancel=cancel)

    def _gizmo_handle_under_mouse(self, node, mouse_x: float, mouse_y: float) -> str | None:
        return self._get_viewport_controller().gizmo_handle_under_mouse(node, mouse_x, mouse_y)

    def _update_viewport_input(self) -> None:
        self._get_viewport_controller().update_viewport_input()

    # ==========================================================
    # INSPECTOR
    # ==========================================================

    def _build_inspector(self) -> None:
        self._get_inspector_controller().build()

    def _refresh_inspector(self) -> None:
        self._get_inspector_controller().refresh()

    def _on_selection_changed(self, node, _previous) -> None:
        self._get_workspace_controller().on_selection_changed(node, _previous)

    # ==========================================================
    # BOTTOM DOCK
    # ==========================================================

    def _build_bottom_dock(self) -> None:
        self._get_bottom_dock_controller()._build_bottom_dock()

    def _build_asset_drag_overlay(self) -> None:
        self._get_asset_browser_controller().build_drag_overlay()
    # ==========================================================
    # STATUS
    # ==========================================================

    def _build_status_bar(self) -> None:
        self._get_workspace_controller().build_status_bar()

    # ==========================================================
    # REFRESH
    # ==========================================================

    def _refresh_document_ui(self) -> None:
        self._get_workspace_controller().refresh_document_ui()

    def _refresh_asset_summary(self) -> None:
        # Kept as the document-workflow refresh hook.
        self._refresh_asset_browser(
            preserve_selection=True
        )

    def _refresh_asset_browser(
        self,
        preserve_selection: bool = True,
    ) -> None:
        self._get_asset_browser_controller().refresh(preserve_selection)
    def _on_asset_search_changed(self, text: str) -> None:
        self._get_asset_browser_controller().on_search_changed(text)
    def _asset_go_up(self) -> None:
        self._get_asset_browser_controller().go_up()
    def _on_asset_selected(
        self,
        index: int,
        label: str | None,
    ) -> None:
        self._get_asset_browser_controller().on_selected(index, label)
    def _on_asset_activated(self, index: int, label: str) -> None:
        self._get_asset_browser_controller().on_activated(index, label)
    def _unique_node_name(self, base_name: str) -> str:
        return self._get_workspace_controller().unique_node_name(base_name)

    def _sync_prefab_instance_overrides(self, node=None) -> None:
        self._get_workspace_controller().sync_prefab_instance_overrides(node)

    def _sync_all_prefab_instance_overrides(self) -> None:
        self._get_workspace_controller().sync_all_prefab_instance_overrides()

    def _update_asset_drag_input(self) -> None:
        self._get_asset_browser_controller().update_drag_input()
    def _asset_context_open_selected(self) -> None:
        self._get_asset_browser_controller().context_open_selected()
    def _asset_context_reveal_selected(self) -> None:
        self._get_asset_browser_controller().context_reveal_selected()
    def _update_asset_context_input(self) -> None:
        self._get_asset_browser_controller().update_context_input()
    @property
    def asset_drag_payload(self):
        """Selected asset payload for viewport and inspector drop targets."""
        return self._get_asset_browser_controller().drag_payload
    # ==========================================================
    # HELPERS
    # ==========================================================

    def _panel_title(self, parent: Panel, text: str) -> Label:
        label = parent.create_child(
            f"{text.replace(' ', '')}Title",
            node_type=Label,
        )
        label.text = text
        label.scale = 0.78
        label.anchor = (0.0, 0.0)
        label.pivot = (0.0, 0.0)
        return label

    def _button(self, parent: Panel, name: str, text: str, callback) -> Button:
        button = parent.create_child(name, node_type=Button)
        button.text = text
        button.text_scale = 0.72
        button.normal_background = BUTTON_BACKGROUND
        button.hover_background = BUTTON_HOVER
        button.pressed_background = BUTTON_PRESSED
        button.focus_background = BUTTON_HOVER
        button.focus_border_color = ACCENT
        button.on_click = callback
        return button

    def _apply_bottom_tab_visibility(self) -> None:
        self._get_bottom_dock_controller()._apply_bottom_tab_visibility()

    def _set_bottom_tab(self, tab: str) -> None:
        self._get_bottom_dock_controller()._set_bottom_tab(tab)

    def _refresh_console_output(self) -> None:
        self._get_bottom_dock_controller()._refresh_console_output()

    def _clear_editor_console(self) -> None:
        self._get_bottom_dock_controller()._clear_editor_console()

    def _toggle_play_mode(self) -> None:
        self._get_toolbar_controller().toggle_play_mode()


    def _start_play_mode(self) -> None:
        self._get_toolbar_controller().start_play_mode()


    def _stop_play_mode(self) -> None:
        self._get_toolbar_controller().stop_play_mode()


    def _sync_play_button(self) -> None:
        self._get_toolbar_controller().sync_play_button()


    def _open_editor_tool(self, flag: str, display_name: str) -> None:
        self._get_toolbar_controller().open_editor_tool(flag, display_name)


    def _open_tilemap_editor(self) -> None:
        self._get_toolbar_controller().open_tilemap_editor()


    # ==========================================================
    # LAYOUT
    # ==========================================================

    def update(self, delta_time: float) -> None:
        super().update(delta_time)
        self._sync_layout()
        self._sync_play_button()
        self._get_bottom_dock_controller().update()
        self._get_animation_controller().update(delta_time)
        self._update_viewport_input()
        self._update_asset_drag_input()
        self._update_asset_context_input()
        if getattr(self.add_node_dialog, "is_open", False):
            self._sync_add_node_dialog_layout()

    def render(self, renderer) -> None:
        self._sync_layout()
        super().render(renderer)

    def _sync_layout(self) -> None:
        self._get_workspace_controller().sync_layout()

    def _sync_toolbar_layout(self, width: float) -> None:
        self._get_toolbar_controller().sync_layout(width)


    def _sync_scene_tree_layout(self, width: float, height: float) -> None:
        self._get_scene_tree_controller().sync_layout(width, height)

    def _sync_viewport_layout(self, width: float, height: float) -> None:
        self._get_viewport_controller().sync_viewport_layout(width, height)

    def _sync_inspector_layout(self, width: float, height: float) -> None:
        self._get_inspector_controller().sync_layout(width, height)

    def _sync_bottom_layout(self, width: float, height: float) -> None:
        self._get_bottom_dock_controller()._sync_bottom_layout(width, height)

    def _sync_status_layout(self, width: float) -> None:
        self._get_workspace_controller().sync_status_layout(width)
