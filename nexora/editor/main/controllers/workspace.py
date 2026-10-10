from __future__ import annotations

from nexora.editor.commands import prefab_instance_overrides_for_node
from nexora.nodes import ConfirmDialog, Dialog, FileDialog, Label, ListView, TextInput


class WorkspaceController:
    """Owns editor-shell wiring shared across document, selection, and layout."""

    def __init__(self, scene) -> None:
        self.scene = scene

    def build_dialogs(self) -> None:
        scene = self.scene
        document = scene._get_document_controller()
        tree = scene._get_scene_tree_controller()

        scene.new_scene_dialog = scene.ui.create_child(
            "NewSceneDialog",
            node_type=Dialog,
        )
        scene.new_scene_dialog.title = "New Scene"
        scene.new_scene_dialog.confirm_text = "Create"
        scene.new_scene_dialog.dialog_size = (500.0, 235.0)

        scene.new_scene_name = scene.new_scene_dialog.content.create_child(
            "SceneName",
            node_type=TextInput,
        )
        scene.new_scene_name.placeholder = "Scene name"
        scene.new_scene_name.size = (430.0, 44.0)
        scene.new_scene_name.anchor = (0.5, 0.5)
        scene.new_scene_name.pivot = (0.5, 0.5)
        scene.new_scene_name.on_submit = lambda _text: scene.new_scene_dialog.confirm()
        scene.new_scene_dialog.on_confirm = document.create_scene_from_dialog

        scene.add_node_dialog = scene.ui.create_child(
            "AddNodeDialog",
            node_type=Dialog,
        )
        scene.add_node_dialog.title = "Add Node"
        scene.add_node_dialog.confirm_text = "Add"
        scene.add_node_dialog.dialog_size = (540.0, 430.0)

        scene.add_node_parent_label = scene.add_node_dialog.content.create_child(
            "ParentLabel",
            node_type=Label,
        )
        scene.add_node_parent_label.anchor = (0.0, 0.0)
        scene.add_node_parent_label.pivot = (0.0, 0.0)
        scene.add_node_parent_label.scale = 0.72

        scene.add_node_type_list = scene.add_node_dialog.content.create_child(
            "NodeTypes",
            node_type=ListView,
        )
        scene.add_node_type_list.item_height = 30.0
        scene.add_node_type_list.text_scale = 0.68
        scene.add_node_type_list.padding_left = 5.0
        scene.add_node_type_list.padding_right = 5.0
        scene.add_node_type_list.padding_top = 5.0
        scene.add_node_type_list.padding_bottom = 5.0
        scene.add_node_type_list.on_change = tree.on_add_node_type_selected

        scene.add_node_name = scene.add_node_dialog.content.create_child(
            "NodeName",
            node_type=TextInput,
        )
        scene.add_node_name.placeholder = "Node name"
        scene.add_node_name.on_submit = lambda _text: scene.add_node_dialog.confirm()
        scene.add_node_dialog.on_confirm = tree.confirm_add_node

        scene.rename_node_dialog = scene.ui.create_child(
            "RenameNodeDialog",
            node_type=Dialog,
        )
        scene.rename_node_dialog.title = "Rename Node"
        scene.rename_node_dialog.confirm_text = "Rename"
        scene.rename_node_dialog.dialog_size = (500.0, 235.0)
        scene.rename_node_name = scene.rename_node_dialog.content.create_child(
            "NodeName",
            node_type=TextInput,
        )
        scene.rename_node_name.placeholder = "Node name"
        scene.rename_node_name.size = (430.0, 44.0)
        scene.rename_node_name.anchor = (0.5, 0.5)
        scene.rename_node_name.pivot = (0.5, 0.5)
        scene.rename_node_name.on_submit = lambda _text: scene.rename_node_dialog.confirm()
        scene.rename_node_dialog.on_confirm = tree.confirm_rename_node

        scene.delete_node_dialog = scene.ui.create_child(
            "DeleteNodeDialog",
            node_type=ConfirmDialog,
        )
        scene.delete_node_dialog.title = "Delete Node"
        scene.delete_node_dialog.confirm_text = "Delete"
        scene.delete_node_dialog.cancel_text = "Cancel"
        scene.delete_node_dialog.on_confirm = tree.confirm_delete_node

        scene.open_scene_dialog = scene.ui.create_child(
            "OpenSceneDialog",
            node_type=FileDialog,
        )
        scene.open_scene_dialog.file_selected.connect(document.on_open_scene_selected)

        scene.save_scene_dialog = scene.ui.create_child(
            "SaveSceneDialog",
            node_type=FileDialog,
        )
        scene.save_scene_dialog.file_selected.connect(document.on_save_scene_selected)

        scene.save_prefab_dialog = scene.ui.create_child(
            "SavePrefabDialog",
            node_type=FileDialog,
        )
        scene.save_prefab_dialog.file_selected.connect(document.on_save_prefab_selected)

        scene.unsaved_dialog = scene.ui.create_child(
            "UnsavedDialog",
            node_type=ConfirmDialog,
        )
        scene.unsaved_dialog.title = "Unsaved Changes"
        scene.unsaved_dialog.confirm_text = "Discard"
        scene.unsaved_dialog.cancel_text = "Cancel"
        scene.unsaved_dialog.message = (
            "The current scene has unsaved changes.\n"
            "Discard them and continue?"
        )
        scene.unsaved_dialog.on_confirm = document.continue_pending_action
        scene.unsaved_dialog.on_cancel = document.clear_pending_action

        scene.error_dialog = scene.ui.create_child(
            "EditorErrorDialog",
            node_type=ConfirmDialog,
        )
        scene.error_dialog.title = "Editor Error"
        scene.error_dialog.confirm_text = "OK"
        scene.error_dialog.show_cancel_button = False


    def any_editor_dialog_open(self) -> bool:
        scene = self.scene
        names = (
            "new_scene_dialog",
            "add_node_dialog",
            "rename_node_dialog",
            "delete_node_dialog",
            "open_scene_dialog",
            "save_scene_dialog",
            "save_prefab_dialog",
            "unsaved_dialog",
            "error_dialog",
        )
        return any(
            bool(getattr(getattr(scene, name, None), "is_open", False))
            for name in names
        )

    def serialization_context(self) -> dict:
        scene = self.scene
        engine = scene.game.engine
        context = {
            "game": scene.game,
            "engine": engine,
            "renderer": scene.game.renderer,
            "input": scene.game.input,
            "scene": scene.document.scene,
        }
        if engine is not None:
            context["assets"] = engine.assets
            context["audio"] = engine.audio
        return context

    def show_error(self, message: str) -> None:
        scene = self.scene
        scene.error_dialog.message = str(message)
        scene.error_dialog.open()

    def build_status_bar(self) -> None:
        scene = self.scene
        scene.status_label = scene.status_bar.create_child(
            "StatusLabel",
            node_type=Label,
        )
        scene.status_label.text = "Ready"
        scene.status_label.scale = 0.62
        scene.status_label.anchor = (0.0, 0.5)
        scene.status_label.pivot = (0.0, 0.5)

        scene.engine_label = scene.status_bar.create_child(
            "EngineLabel",
            node_type=Label,
        )
        scene.engine_label.text = "Nexora Editor v0.10"
        scene.engine_label.scale = 0.62
        scene.engine_label.anchor = (1.0, 0.5)
        scene.engine_label.pivot = (1.0, 0.5)

    def refresh_document_ui(self) -> None:
        scene = self.scene
        scene._refresh_scene_tree()
        scene._refresh_inspector()
        scene._refresh_animation_panel()
        scene.document_label.text = f"{scene.project.name}  |  {scene.document.title}"
        scene.viewport_subtitle.text = f"Editing: {scene.document.display_name}"
        scene._refresh_asset_summary()

    def on_selection_changed(self, node, _previous) -> None:
        scene = self.scene
        scene._get_inspector_controller().on_selection_changed()
        scene._refresh_animation_panel()

        if node is None:
            scene.status_label.text = "Selection cleared"
            return

        scene.status_label.text = (
            f"Selected {getattr(node, 'name', type(node).__name__)}"
        )

    def unique_node_name(self, base_name: str) -> str:
        scene = self.scene
        base = str(base_name).strip() or "Sprite"
        existing = {str(node.name) for node in scene._iter_viewport_nodes()}
        if base not in existing:
            return base
        index = 2
        while f"{base}_{index}" in existing:
            index += 1
        return f"{base}_{index}"

    def sync_prefab_instance_overrides(self, node=None) -> None:
        scene = self.scene
        node = scene.selection.selected if node is None else node

        if node is None or not getattr(node, "_nexora_prefab_source", None):
            return

        try:
            node._nexora_prefab_overrides = prefab_instance_overrides_for_node(
                node,
                scene.game.scene_serializer.registry,
            )
        except Exception:
            return

    def sync_all_prefab_instance_overrides(self) -> None:
        scene = self.scene
        for node in scene._iter_viewport_nodes():
            self.sync_prefab_instance_overrides(node)

    def sync_layout(self) -> None:
        scene = self.scene
        renderer = scene.game.renderer
        if renderer is None:
            return

        width = float(renderer.width)
        height = float(renderer.height)
        size = (width, height)
        if size == scene._last_size:
            return
        scene._last_size = size

        scene.background.size = size
        scene.background.anchor = (0.5, 0.5)
        scene.background.pivot = (0.5, 0.5)

        scene.toolbar.anchor = (0.5, 0.0)
        scene.toolbar.pivot = (0.5, 0.0)
        scene.toolbar.size = (width, scene.TOOLBAR_HEIGHT)
        scene.toolbar.position = (0.0, scene.TOOLBAR_HEIGHT / 2.0)

        scene.status_bar.anchor = (0.5, 1.0)
        scene.status_bar.pivot = (0.5, 1.0)
        scene.status_bar.size = (width, scene.STATUS_HEIGHT)
        scene.status_bar.position = (0.0, -scene.STATUS_HEIGHT / 2.0)

        body_top = scene.TOOLBAR_HEIGHT + scene.GAP
        body_bottom = height - scene.STATUS_HEIGHT - scene.GAP
        body_height = max(0.0, body_bottom - body_top)
        bottom_h = min(scene.BOTTOM_HEIGHT, max(100.0, body_height * 0.28))
        upper_h = max(0.0, body_height - bottom_h - scene.GAP)

        left_w = min(scene.LEFT_WIDTH, width * 0.25)
        right_w = min(scene.RIGHT_WIDTH, width * 0.3)
        center_w = max(0.0, width - left_w - right_w - scene.GAP * 2.0)

        scene.scene_tree.anchor = (0.0, 0.0)
        scene.scene_tree.pivot = (0.0, 0.0)
        scene.scene_tree.size = (left_w, upper_h)
        scene.scene_tree.position = (left_w / 2.0, body_top + upper_h / 2.0)

        scene.viewport.anchor = (0.0, 0.0)
        scene.viewport.pivot = (0.0, 0.0)
        scene.viewport.size = (center_w, upper_h)
        scene.viewport.position = (
            left_w + scene.GAP + center_w / 2.0,
            body_top + upper_h / 2.0,
        )

        scene.inspector.anchor = (0.0, 0.0)
        scene.inspector.pivot = (0.0, 0.0)
        scene.inspector.size = (right_w, upper_h)
        scene.inspector.position = (
            left_w + scene.GAP + center_w + scene.GAP + right_w / 2.0,
            body_top + upper_h / 2.0,
        )

        scene.bottom_dock.anchor = (0.0, 0.0)
        scene.bottom_dock.pivot = (0.0, 0.0)
        scene.bottom_dock.size = (width, bottom_h)
        scene.bottom_dock.position = (
            width / 2.0,
            body_top + upper_h + scene.GAP + bottom_h / 2.0,
        )

        scene._sync_toolbar_layout(width)
        scene._sync_scene_tree_layout(left_w, upper_h)
        scene._sync_viewport_layout(center_w, upper_h)
        scene._sync_inspector_layout(right_w, upper_h)
        scene._sync_bottom_layout(width, bottom_h)
        scene._sync_status_layout(width)

    def sync_status_layout(self, width: float) -> None:
        scene = self.scene
        scene.status_label.position = (12.0, 0.0)
        scene.engine_label.position = (-12.0, 0.0)
