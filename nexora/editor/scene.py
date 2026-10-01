from __future__ import annotations

from pathlib import Path

from nexora.nodes import (
    Button,
    CheckBox,
    ConfirmDialog,
    Dialog,
    FileDialog,
    Label,
    ListView,
    Panel,
    TextInput,
)
from nexora.nodes.ui.containers.scroll_view import ScrollView
from nexora.scene import Scene

from nexora.editor.asset_browser import (
    AssetBrowserModel,
    AssetPreview,
    format_file_size,
    reveal_in_file_manager,
)

from nexora.editor.model import (
    EditorDocument,
    EditorProjectContext,
    ProjectModel,
    SelectionService,
)

from nexora.editor.commands import (
    AddImageSpriteCommand,
    AnimationClipCommand,
    AddNodeCommand,
    CommandStack,
    DeleteNodeCommand,
    InstantiatePrefabCommand,
    RenameNodeCommand,
    SetPropertyCommand,
    TileMapAssetCommand,
    TransformNodeCommand,
    TransformSnapshot,
    prefab_instance_overrides_for_node,
)

from nexora.editor.inspector import (
    PropertyPathAccessor,
    create_default_inspector_registry,
)
from nexora.editor.viewport import (
    EditorViewportCanvas,
    EditorViewportState,
    GIZMO_MOVE,
    GIZMO_ROTATE,
    GIZMO_SCALE,
    drag_angle_degrees,
    gizmo_hit_test,
    node_hit_distance,
    world_delta_to_local,
)
from nexora.nodes.node import Node
from nexora.nodes.world.tilemap_node import TileMapNode
from nexora.nodes.texture.animated_sprite import AnimatedSprite
from nexora.animation import AnimationClip, AnimationFrame, AnimationPlayer
from nexora.tilemap import TileMap, TileProjection, TileSet

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


class EditorScene(Scene):
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
        self.inspector_registry = create_default_inspector_registry(Node)
        self._inspector_controls: dict[str, object] = {}
        self._inspector_labels: dict[str, Label] = {}
        self._inspector_groups: dict[str, Label] = {}
        self._inspector_syncing = False
        self._scene_entries = []
        self._last_size = (-1.0, -1.0)
        self._pending_action = None
        self._prefab_save_node = None

        self.viewport_state = EditorViewportState()

        self.viewport_tool = GIZMO_MOVE
        self.viewport_snap_enabled = False
        self.viewport_move_snap = 32.0
        self.viewport_rotate_snap = 15.0
        self.viewport_scale_snap = 0.10

        self._gizmo_drag = None
        self._gizmo_active_handle = None

        self.asset_browser = AssetBrowserModel(
            self.project_path
        )
        self._asset_entries = []
        self._selected_asset = None
        self._asset_drag_payload = None
        self._bottom_tab = "assets"
        self._animation_clip_name = None
        self._asset_pointer_press = None
        self._asset_drag_active = False
        self._asset_drag_entry = None
        self._asset_drag_threshold = 7.0

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

        self.selection.changed.connect(self._on_selection_changed)
        self._refresh_document_ui()

    def _style_panel(self, panel: Panel) -> None:
        panel.background = PANEL_BACKGROUND
        panel.border_color = PANEL_BORDER
        panel.border_width = 1.0

    # ==========================================================
    # TOOLBAR
    # ==========================================================

    def _build_toolbar(self) -> None:
        self.brand_label = self.toolbar.create_child("Brand", node_type=Label)
        self.brand_label.text = "NEXORA"
        self.brand_label.scale = 0.9
        self.brand_label.anchor = (0.0, 0.5)
        self.brand_label.pivot = (0.0, 0.5)

        self.new_button = self._button(
            self.toolbar,
            "NewButton",
            "New",
            self.request_new_scene,
        )
        self.open_button = self._button(
            self.toolbar,
            "OpenButton",
            "Open",
            self.request_open_scene,
        )
        self.save_button = self._button(
            self.toolbar,
            "SaveButton",
            "Save",
            self.save_scene,
        )
        self.save_as_button = self._button(
            self.toolbar,
            "SaveAsButton",
            "Save As",
            self.save_scene_as,
        )
        self.save_prefab_button = self._button(
            self.toolbar,
            "SavePrefabButton",
            "Prefab",
            self.save_selected_prefab,
        )
        self.undo_button = self._button(
            self.toolbar,
            "UndoButton",
            "Undo",
            self.undo,
        )
        self.redo_button = self._button(
            self.toolbar,
            "RedoButton",
            "Redo",
            self.redo,
        )
        self.play_button = self._button(
            self.toolbar,
            "PlayButton",
            "Run",
            self._toggle_play_mode,
        )
        self.tilemap_editor_button = self._button(
            self.toolbar,
            "TileMapEditorButton",
            "TileMap Editor",
            self._open_tilemap_editor,
        )

        self.document_label = self.toolbar.create_child(
            "DocumentLabel",
            node_type=Label,
        )
        self.document_label.scale = 0.72
        self.document_label.anchor = (1.0, 0.5)
        self.document_label.pivot = (1.0, 0.5)

    # ==========================================================
    # DIALOGS
    # ==========================================================

    def _build_dialogs(self) -> None:
        self.new_scene_dialog = self.ui.create_child(
            "NewSceneDialog",
            node_type=Dialog,
        )
        self.new_scene_dialog.title = "New Scene"
        self.new_scene_dialog.confirm_text = "Create"
        self.new_scene_dialog.dialog_size = (500.0, 235.0)

        self.new_scene_name = self.new_scene_dialog.content.create_child(
            "SceneName",
            node_type=TextInput,
        )
        self.new_scene_name.placeholder = "Scene name"
        self.new_scene_name.size = (430.0, 44.0)
        self.new_scene_name.anchor = (0.5, 0.5)
        self.new_scene_name.pivot = (0.5, 0.5)
        self.new_scene_name.on_submit = lambda _text: self.new_scene_dialog.confirm()
        self.new_scene_dialog.on_confirm = self._create_scene_from_dialog

        self.add_node_dialog = self.ui.create_child(
            "AddNodeDialog",
            node_type=Dialog,
        )
        self.add_node_dialog.title = "Add Node"
        self.add_node_dialog.confirm_text = "Add"
        self.add_node_dialog.dialog_size = (540.0, 430.0)

        self.add_node_parent_label = self.add_node_dialog.content.create_child(
            "ParentLabel",
            node_type=Label,
        )
        self.add_node_parent_label.anchor = (0.0, 0.0)
        self.add_node_parent_label.pivot = (0.0, 0.0)
        self.add_node_parent_label.scale = 0.72

        self.add_node_type_list = self.add_node_dialog.content.create_child(
            "NodeTypes",
            node_type=ListView,
        )
        self.add_node_type_list.item_height = 30.0
        self.add_node_type_list.text_scale = 0.68
        self.add_node_type_list.padding_left = 5.0
        self.add_node_type_list.padding_right = 5.0
        self.add_node_type_list.padding_top = 5.0
        self.add_node_type_list.padding_bottom = 5.0
        self.add_node_type_list.on_change = self._on_add_node_type_selected

        self.add_node_name = self.add_node_dialog.content.create_child(
            "NodeName",
            node_type=TextInput,
        )
        self.add_node_name.placeholder = "Node name"
        self.add_node_name.on_submit = lambda _text: self.add_node_dialog.confirm()
        self.add_node_dialog.on_confirm = self._confirm_add_node

        self.rename_node_dialog = self.ui.create_child(
            "RenameNodeDialog",
            node_type=Dialog,
        )
        self.rename_node_dialog.title = "Rename Node"
        self.rename_node_dialog.confirm_text = "Rename"
        self.rename_node_dialog.dialog_size = (500.0, 235.0)
        self.rename_node_name = self.rename_node_dialog.content.create_child(
            "NodeName",
            node_type=TextInput,
        )
        self.rename_node_name.placeholder = "Node name"
        self.rename_node_name.size = (430.0, 44.0)
        self.rename_node_name.anchor = (0.5, 0.5)
        self.rename_node_name.pivot = (0.5, 0.5)
        self.rename_node_name.on_submit = lambda _text: self.rename_node_dialog.confirm()
        self.rename_node_dialog.on_confirm = self._confirm_rename_node

        self.delete_node_dialog = self.ui.create_child(
            "DeleteNodeDialog",
            node_type=ConfirmDialog,
        )
        self.delete_node_dialog.title = "Delete Node"
        self.delete_node_dialog.confirm_text = "Delete"
        self.delete_node_dialog.cancel_text = "Cancel"
        self.delete_node_dialog.on_confirm = self._confirm_delete_node

        self.open_scene_dialog = self.ui.create_child(
            "OpenSceneDialog",
            node_type=FileDialog,
        )
        self.open_scene_dialog.file_selected.connect(self._on_open_scene_selected)

        self.save_scene_dialog = self.ui.create_child(
            "SaveSceneDialog",
            node_type=FileDialog,
        )
        self.save_scene_dialog.file_selected.connect(self._on_save_scene_selected)

        self.save_prefab_dialog = self.ui.create_child(
            "SavePrefabDialog",
            node_type=FileDialog,
        )
        self.save_prefab_dialog.file_selected.connect(
            self._on_save_prefab_selected
        )

        self.unsaved_dialog = self.ui.create_child(
            "UnsavedDialog",
            node_type=ConfirmDialog,
        )
        self.unsaved_dialog.title = "Unsaved Changes"
        self.unsaved_dialog.confirm_text = "Discard"
        self.unsaved_dialog.cancel_text = "Cancel"
        self.unsaved_dialog.message = (
            "The current scene has unsaved changes.\n"
            "Discard them and continue?"
        )
        self.unsaved_dialog.on_confirm = self._continue_pending_action
        self.unsaved_dialog.on_cancel = self._clear_pending_action

        self.error_dialog = self.ui.create_child(
            "EditorErrorDialog",
            node_type=ConfirmDialog,
        )
        self.error_dialog.title = "Editor Error"
        self.error_dialog.confirm_text = "OK"
        self.error_dialog.show_cancel_button = False

    def _serialization_context(self) -> dict:
        engine = self.game.engine
        context = {"game": self.game, "engine": engine, "renderer": self.game.renderer, "input": self.game.input, "scene": self.document.scene}
        if engine is not None:
            context["assets"] = engine.assets
            context["audio"] = engine.audio
        return context

    # ==========================================================
    # DOCUMENT WORKFLOW
    # ==========================================================

    def _run_after_dirty_check(self, action) -> None:
        if self.document.dirty:
            self._pending_action = action
            self.unsaved_dialog.open()
            return
        action()

    def _continue_pending_action(self) -> None:
        action = self._pending_action
        self._pending_action = None
        if action is not None:
            action()

    def _clear_pending_action(self) -> None:
        self._pending_action = None

    def request_new_scene(self) -> None:
        self._run_after_dirty_check(self._open_new_scene_dialog)

    def _open_new_scene_dialog(self) -> None:
        self.new_scene_name.set_text("Untitled", emit=False)
        self.new_scene_dialog.open(focus=self.new_scene_name)

    def _create_scene_from_dialog(self) -> None:
        name = self.new_scene_name.text.strip() or "Untitled"
        self.document.new(name)
        self.commands.clear()
        self.selection.clear()
        self._refresh_document_ui()
        self.status_label.text = f"Created scene {name}"

    def request_open_scene(self) -> None:
        self._run_after_dirty_check(self._open_scene_file_dialog)

    def _scene_start_directory(self) -> Path:
        scenes = self.project_context.scenes_root
        if scenes.is_dir():
            return scenes
        return self.project_path

    def _open_scene_file_dialog(self) -> None:
        self.open_scene_dialog.configure(
            mode="open",
            root_path=self.project_path,
            current_path=self._scene_start_directory(),
            extensions=(".nxscene",),
            title="Open Scene",
        )
        self.open_scene_dialog.open()

    def _on_open_scene_selected(self, _dialog, path: Path) -> None:
        try:
            self.document.load(self.game.scene_serializer, path, context=self._serialization_context())
        except Exception as exc:
            self._show_error(f"Could not open scene:\n{exc}")
            return

        self.commands.clear()
        self.selection.clear()
        self._refresh_document_ui()
        self.status_label.text = f"Opened {path.name}"

    def save_scene(self) -> None:
        if self.document.path is None:
            self.save_scene_as()
            return

        self._sync_all_prefab_instance_overrides()

        try:
            path = self.document.save(self.game.scene_serializer)
        except Exception as exc:
            self._show_error(f"Could not save scene:\n{exc}")
            return

        self._refresh_document_ui()
        self.status_label.text = f"Saved {path.name}"

    def save_selected_prefab(self) -> None:
        node = self._editable_selected_node()
        if node is None:
            self.status_label.text = "Select a node to save as a prefab first"
            return

        start = self.project_context.prefabs_root
        if not start.is_dir():
            start = self.project_context.assets_root
        if not start.is_dir():
            start = self.project_path

        self._prefab_save_node = node
        self.save_prefab_dialog.configure(
            mode="save",
            root_path=self.project_path,
            current_path=start,
            extensions=(".nxprefab",),
            title="Save Prefab As",
        )
        self.save_prefab_dialog.filename_input.set_text(
            f"{node.name}.nxprefab",
            emit=False,
        )
        self.save_prefab_dialog.open(
            focus=self.save_prefab_dialog.filename_input
        )

    def _on_save_prefab_selected(self, _dialog, path: Path) -> None:
        node = self._prefab_save_node
        self._prefab_save_node = None

        if node is None:
            return

        try:
            saved = self.game.scene_serializer.prefabs.save(node, path)
        except Exception as exc:
            self._show_error(f"Could not save prefab:\n{exc}")
            return

        self._refresh_asset_browser(preserve_selection=False)
        self.status_label.text = f"Saved prefab {saved.name}"

    def save_scene_as(self) -> None:
        start = self._scene_start_directory()
        self.save_scene_dialog.configure(
            mode="save",
            root_path=self.project_path,
            current_path=start,
            extensions=(".nxscene",),
            title="Save Scene As",
        )
        self.save_scene_dialog.filename_input.set_text(
            f"{self.document.display_name}.nxscene",
            emit=False,
        )
        self.save_scene_dialog.open(focus=self.save_scene_dialog.filename_input)

    def _on_save_scene_selected(self, _dialog, path: Path) -> None:
        self._sync_all_prefab_instance_overrides()

        try:
            saved = self.document.save_as(self.game.scene_serializer, path)
        except Exception as exc:
            self._show_error(f"Could not save scene:\n{exc}")
            return

        self._refresh_document_ui()
        self.status_label.text = f"Saved {saved.name}"

    def _show_error(self, message: str) -> None:
        self.error_dialog.message = str(message)
        self.error_dialog.open()

    # ==========================================================
    # SCENE TREE
    # ==========================================================

    def _build_scene_tree(self) -> None:
        self.scene_title = self._panel_title(self.scene_tree, "Scene")

        self.add_node_button = self._button(
            self.scene_tree,
            "AddNodeButton",
            "+",
            self.open_add_node_dialog,
        )
        self.rename_node_button = self._button(
            self.scene_tree,
            "RenameNodeButton",
            "Rename",
            self.open_rename_node_dialog,
        )
        self.delete_node_button = self._button(
            self.scene_tree,
            "DeleteNodeButton",
            "Delete",
            self.request_delete_node,
        )

        self.scene_list = self.scene_tree.create_child(
            "SceneList",
            node_type=ListView,
        )
        self.scene_list.item_height = 30.0
        self.scene_list.spacing = 1.0
        self.scene_list.padding_left = 6.0
        self.scene_list.padding_right = 6.0
        self.scene_list.padding_top = 6.0
        self.scene_list.padding_bottom = 6.0
        self.scene_list.text_padding_left = 8.0
        self.scene_list.text_scale = 0.68
        self.scene_list.on_change = self._on_scene_tree_selected

    def _refresh_scene_tree(self) -> None:
        selected = self.selection.selected
        self._scene_entries = list(self.document.iter_tree_entries())
        self.scene_list.set_items([entry.label for entry in self._scene_entries])

        if selected is None:
            self.scene_list.selected_index = -1
            return

        for index, entry in enumerate(self._scene_entries):
            if entry.node is selected:
                self.scene_list.set_selected_index(index, emit=False)
                break

    def _on_scene_tree_selected(self, index: int, _label: str | None) -> None:
        if not (0 <= index < len(self._scene_entries)):
            self.selection.clear()
            return
        self.selection.select(self._scene_entries[index].node)

    # ==========================================================
    # NODE EDITING / UNDO REDO
    # ==========================================================

    def _on_add_node_type_selected(self, _index: int, label: str | None) -> None:
        """Keep the suggested node name in sync with the selected type."""

        if label:
            self.add_node_name.set_text(str(label), emit=False)

    def _editable_selected_node(self):
        node = self.selection.selected
        if node is None:
            return None
        if node is self.document.scene.root or node is self.document.scene.ui:
            return None
        return node

    def _selected_parent_for_add(self):
        selected = self.selection.selected
        if selected is None:
            return self.document.scene.root
        if getattr(selected, "world", None) is self.document.scene.world:
            return selected
        return self.document.scene.root

    def open_add_node_dialog(self) -> None:
        parent = self._selected_parent_for_add()
        registry = self.game.scene_serializer.registry
        type_ids = list(registry.registered_type_ids())
        if not type_ids:
            self._show_error("No serializable node types are registered.")
            return

        self.add_node_parent_label.text = f"Parent: {parent.name}"
        self.add_node_type_list.set_items(type_ids)
        self.add_node_type_list.set_selected_index(0, emit=False)
        self.add_node_name.set_text(type_ids[0], emit=False)
        self._sync_add_node_dialog_layout()
        self.add_node_dialog.open(focus=self.add_node_name)

    def _confirm_add_node(self) -> None:
        index = self.add_node_type_list.selected_index
        if not (0 <= index < len(self.add_node_type_list.items)):
            return
        type_id = self.add_node_type_list.items[index]
        name = self.add_node_name.text.strip() or type_id
        parent = self._selected_parent_for_add()
        try:
            configure = (
                self._configure_default_tilemap_node
                if type_id == "TileMapNode"
                else None
            )
            command = AddNodeCommand(
                parent=parent,
                registry=self.game.scene_serializer.registry,
                type_id=type_id,
                name=name,
                context=self._serialization_context(),
                configure=configure,
            )
            node = self.commands.execute(command)
        except Exception as exc:
            self._show_error(f"Could not add node:\n{exc}")
            return

        self.document.mark_dirty()
        self.selection.select(node)
        self._refresh_document_ui()
        self.status_label.text = f"Added {name}"

    def _configure_default_tilemap_node(self, node: TileMapNode) -> None:
        """Create a usable starter map when adding a TileMapNode in-editor."""

        candidates = (
            "demo_sprite.png",
            "world/isometric_tiles.png",
        )
        texture_asset = next(
            (
                candidate
                for candidate in candidates
                if self.project_context.resolve_asset(candidate).is_file()
            ),
            None,
        )
        if texture_asset is None:
            raise FileNotFoundError(
                "No starter texture found in the project's assets folder."
            )

        tilemap = TileMap(
            name=f"{node.name}Map",
            width=16,
            height=16,
            tile_width=32,
            tile_height=32,
            projection=TileProjection.ANGLED_2D,
        )
        tilemap.create_layer("ground")

        if texture_asset == "demo_sprite.png":
            columns = rows = 3
        else:
            columns = rows = 1

        tileset = TileSet(
            name=f"{node.name}Tiles",
            columns=columns,
            rows=rows,
            tile_width=32,
            tile_height=32,
            texture_asset=texture_asset,
        )
        assets = self.game.engine.assets
        texture = assets.texture(texture_asset)
        node.set_map(tilemap, tileset, texture)
        node.centered = True

    def open_rename_node_dialog(self) -> None:
        node = self._editable_selected_node()
        if node is None:
            self.status_label.text = "Select an editable node first"
            return
        self.rename_node_name.set_text(str(node.name), emit=False)
        self.rename_node_dialog.open(focus=self.rename_node_name)

    def _confirm_rename_node(self) -> None:
        node = self._editable_selected_node()
        if node is None:
            return
        new_name = self.rename_node_name.text.strip()
        if not new_name or new_name == str(node.name):
            return
        try:
            self.commands.execute(RenameNodeCommand(node, new_name))
        except Exception as exc:
            self._show_error(f"Could not rename node:\n{exc}")
            return
        self._sync_prefab_instance_overrides(node)
        self.document.mark_dirty()
        self._refresh_document_ui()
        self.status_label.text = f"Renamed node to {new_name}"

    def request_delete_node(self) -> None:
        node = self._editable_selected_node()
        if node is None:
            self.status_label.text = "Select an editable node first"
            return
        self.delete_node_dialog.message = (
            f"Delete '{node.name}' and all of its children?"
        )
        self.delete_node_dialog.open()

    def _confirm_delete_node(self) -> None:
        node = self._editable_selected_node()
        if node is None:
            return
        parent = node.parent
        name = str(node.name)
        try:
            command = DeleteNodeCommand(
                node=node,
                registry=self.game.scene_serializer.registry,
                context=self._serialization_context(),
            )
            self.commands.execute(command)
        except Exception as exc:
            self._show_error(f"Could not delete node:\n{exc}")
            return
        self.selection.select(parent)
        self.document.mark_dirty()
        self._refresh_document_ui()
        self.status_label.text = f"Deleted {name}"

    def undo(self) -> None:
        if not self.commands.can_undo:
            self.status_label.text = "Nothing to undo"
            return
        label = self.commands.undo_label or "command"
        result = self.commands.undo()
        self.document.mark_dirty()
        if result is not None:
            self.selection.select(result)
        else:
            selected = self.selection.selected
            if selected is not None and not self.document.scene.world.is_alive(selected.entity):
                self.selection.clear()
        self._sync_all_prefab_instance_overrides()
        self._refresh_document_ui()
        self.status_label.text = f"Undo: {label}"

    def redo(self) -> None:
        if not self.commands.can_redo:
            self.status_label.text = "Nothing to redo"
            return
        label = self.commands.redo_label or "command"
        result = self.commands.redo()
        self.document.mark_dirty()
        if result is not None:
            self.selection.select(result)
        else:
            selected = self.selection.selected
            if selected is not None and not self.document.scene.world.is_alive(selected.entity):
                self.selection.clear()
        self._sync_all_prefab_instance_overrides()
        self._refresh_document_ui()
        self.status_label.text = f"Redo: {label}"

    def _sync_add_node_dialog_layout(self) -> None:
        if not hasattr(
            self,
            "add_node_dialog",
        ):
            return

        content_w, content_h = (
            self.add_node_dialog.content.size
        )

        self.add_node_parent_label.position = (
            0.0,
            0.0,
        )

        # Leave dedicated space at the bottom for the node-name field.
        # The Dialog itself owns the Cancel/Add button row, so the ListView
        # must not extend into that area.
        list_top = 38.0
        reserved_bottom = 92.0

        list_height = max(
            120.0,
            content_h
            - list_top
            - reserved_bottom,
        )

        self.add_node_type_list.anchor = (
            0.5,
            0.0,
        )

        self.add_node_type_list.pivot = (
            0.5,
            0.5,
        )

        self.add_node_type_list.size = (
            max(
                100.0,
                content_w,
            ),
            list_height,
        )

        self.add_node_type_list.position = (
            0.0,
            list_top
            + list_height / 2.0,
        )

        self.add_node_name.anchor = (
            0.5,
            1.0,
        )

        self.add_node_name.pivot = (
            0.5,
            0.5,
        )

        self.add_node_name.size = (
            max(
                100.0,
                content_w,
            ),
            42.0,
        )

        self.add_node_name.position = (
            0.0,
            -46.0,
        )

    # ==========================================================
    # VIEWPORT
    # ==========================================================

    def _build_viewport(self) -> None:
        # The canvas is created first so it renders above the viewport panel
        # background but below the viewport title / toolbar labels.
        self.viewport_canvas = self.viewport.create_child(
            "ViewportCanvas",
            node_type=EditorViewportCanvas,
        )
        self.viewport_canvas.editor_scene = self

        self.viewport_title = self._panel_title(
            self.viewport,
            "2D Viewport",
        )

        self.viewport_hint = self.viewport.create_child(
            "ViewportHint",
            node_type=Label,
        )
        self.viewport_hint.text = "World origin"
        self.viewport_hint.scale = 0.58
        self.viewport_hint.anchor = (0.5, 0.5)
        self.viewport_hint.pivot = (0.5, 0.5)

        self.viewport_subtitle = self.viewport.create_child(
            "ViewportSubtitle",
            node_type=Label,
        )
        self.viewport_subtitle.scale = 0.62
        self.viewport_subtitle.anchor = (0.0, 0.0)
        self.viewport_subtitle.pivot = (0.0, 0.0)

        self.viewport_controls = self.viewport.create_child(
            "ViewportControls",
            node_type=Label,
        )
        self.viewport_controls.scale = 0.56
        self.viewport_controls.anchor = (1.0, 0.0)
        self.viewport_controls.pivot = (1.0, 0.0)

    def _selected_animation_player(self):
        node = self.selection.selected
        return node if isinstance(node, (AnimationPlayer, AnimatedSprite)) else None

    def _animation_speed_property(self, node) -> str:
        return "speed_scale" if isinstance(node, AnimationPlayer) else "animation_speed"

    def _animation_speed(self, node) -> float:
        return float(
            node.speed_scale
            if isinstance(node, AnimationPlayer)
            else node.animation_speed
        )

    def _add_animation_clip(self) -> None:
        node = self._selected_animation_player()
        if node is None:
            return

        existing = {clip.name for clip in node.animations}
        index = 1
        while f"Animation {index}" in existing:
            index += 1
        name = f"Animation {index}"
        clip = AnimationClip(
            name=name,
            frames=(AnimationFrame(index=0, duration=1.0 / 6.0),),
            loop=True,
        )
        self.commands.execute(AnimationClipCommand(node, clip))
        self.document.mark_dirty()
        self._animation_clip_name = name
        node.play(name, restart=True)
        self._refresh_animation_panel()
        self.status_label.text = f"Created animation: {name}"

    def _refresh_animation_panel(self) -> None:
        if not hasattr(self, "animation_list"):
            return

        player = self._selected_animation_player()
        enabled = player is not None
        for control in (
            self.animation_list,
            self.animation_frame_list,
            self.animation_new_button,
            self.animation_play_button,
            self.animation_pause_button,
            self.animation_stop_button,
            self.animation_speed_input,
        ):
            control.enabled = enabled

        if player is None:
            self.animation_list.set_items([])
            self.animation_frame_list.set_items([])
            self.animation_status_label.text = "Select an AnimatedSprite or AnimationPlayer"
            return

        animations = player.animations
        names = [clip.name for clip in animations]
        self.animation_list.set_items(names)
        if not names:
            self._animation_clip_name = None
            self.animation_frame_list.set_items([])
            self.animation_status_label.text = "No animations - click New"
            return

        if self._animation_clip_name not in names:
            self._animation_clip_name = (
                player.current_animation_name
                if player.current_animation_name in names
                else names[0]
            )

        animation_index = names.index(self._animation_clip_name)
        self.animation_list.set_selected_index(animation_index, emit=False)
        clip = player.get_animation(self._animation_clip_name)
        if clip is None:
            self.animation_frame_list.set_items([])
            return

        self.animation_frame_list.set_items(
            [
                f"Frame {index}  |  source {frame.index}  |  "
                f"{frame.duration * 1000.0:.1f} ms"
                for index, frame in enumerate(clip.frames)
            ]
        )
        self.animation_speed_input.set_text(
            f"{self._animation_speed(player):g}",
            emit=False,
        )
        state = "Playing" if player.playing else "Stopped"
        self.animation_status_label.text = (
            f"{clip.name}  |  {clip.frame_count} frames  |  {state}"
        )

    def _on_animation_selected(self, index: int, _label: str | None) -> None:
        player = self._selected_animation_player()
        if player is None or not (0 <= index < len(player.animations)):
            return
        self._animation_clip_name = player.animations[index].name
        player.play(self._animation_clip_name, restart=True)
        self._refresh_animation_panel()
        self.status_label.text = f"Preview: {self._animation_clip_name}"

    def _on_animation_speed_submitted(self, text: str) -> None:
        player = self._selected_animation_player()
        if player is None:
            return
        try:
            speed = float(str(text).strip().replace(",", "."))
        except ValueError:
            self.status_label.text = "Animation speed must be a number"
            self._refresh_animation_panel()
            return
        if speed <= 0.0:
            self.status_label.text = "Animation speed must be greater than zero"
            self._refresh_animation_panel()
            return
        if speed == self._animation_speed(player):
            return
        property_name = self._animation_speed_property(player)
        self.commands.execute(
            SetPropertyCommand(
                player,
                property_name,
                speed,
                label=f"Set {player.name} Animation Speed",
            )
        )
        self.document.mark_dirty()
        self._refresh_animation_panel()
        self.status_label.text = "Animation speed changed"

    def _play_selected_animation(self) -> None:
        player = self._selected_animation_player()
        if player is None or self._animation_clip_name is None:
            return
        player.play(self._animation_clip_name)
        self._refresh_animation_panel()

    def _pause_selected_animation(self) -> None:
        player = self._selected_animation_player()
        if player is None:
            return
        player.pause()
        self._refresh_animation_panel()

    def _stop_selected_animation(self) -> None:
        player = self._selected_animation_player()
        if player is None:
            return
        player.stop()
        self._refresh_animation_panel()

    def _any_editor_dialog_open(self) -> bool:
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
            bool(getattr(getattr(self, name, None), "is_open", False))
            for name in names
        )

    def _viewport_mouse_centered(self) -> tuple[float, float]:
        mouse_x, mouse_y = self.game.input.mouse_position
        renderer = self.game.renderer
        if renderer is None:
            return 0.0, 0.0
        return (
            float(mouse_x) - float(renderer.width) * 0.5,
            float(mouse_y) - float(renderer.height) * 0.5,
        )

    def _mouse_inside_viewport_canvas(self) -> bool:
        if not hasattr(self, "viewport_canvas"):
            return False
        mouse_x, mouse_y = self._viewport_mouse_centered()
        return self.viewport_canvas.contains_point(
            mouse_x,
            mouse_y,
        )

    def _iter_viewport_nodes(self):
        def walk(node):
            for child in tuple(getattr(node, "children", ())):
                yield from walk(child)
                yield child

        yield from walk(self.document.scene.root)

    def _select_node_from_viewport(self) -> None:
        if not self._mouse_inside_viewport_canvas():
            return

        mouse_x, mouse_y = self._viewport_mouse_centered()
        center_x, center_y = self.viewport_canvas.calculate_position()

        best_node = None
        best_distance = None

        for node in self._iter_viewport_nodes():
            distance = node_hit_distance(
                node,
                mouse_x=mouse_x,
                mouse_y=mouse_y,
                state=self.viewport_state,
                center_x=center_x,
                center_y=center_y,
            )

            if distance is None:
                continue

            if (
                best_distance is None
                or distance < best_distance
            ):
                best_node = node
                best_distance = distance

        if best_node is None:
            self.selection.clear()
        else:
            self.selection.select(best_node)

        self._refresh_scene_tree()

    def _focus_selected_node(self) -> None:
        node = self._selected_viewport_node()
        if node is None:
            self.status_label.text = "Select a node to focus"
            return

        try:
            world_x, world_y = node.world_position
        except Exception:
            self.status_label.text = "Selected node has no world position"
            return

        self.viewport_state.x = float(world_x)
        self.viewport_state.y = float(world_y)
        self.status_label.text = f"Focused {node.name}"

    def _selected_viewport_node(self):
        node = self.selection.selected

        if (
            node is None
            or node is self.document.scene.root
            or node is self.document.scene.ui
        ):
            return None

        return node

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

    def _gizmo_pivot_screen(
        self,
        node,
    ) -> tuple[float, float]:
        world_x, world_y = (
            node.world_position
        )

        center_x, center_y = (
            self.viewport_canvas.calculate_position()
        )

        return self.viewport_state.world_to_screen(
            world_x,
            world_y,
            center_x,
            center_y,
        )

    def _begin_gizmo_drag(
        self,
        node,
        handle: str,
        mouse_x: float,
        mouse_y: float,
    ) -> None:
        pivot_x, pivot_y = (
            self._gizmo_pivot_screen(
                node
            )
        )

        center_x, center_y = (
            self.viewport_canvas.calculate_position()
        )

        mouse_world = (
            self.viewport_state.screen_to_world(
                mouse_x,
                mouse_y,
                center_x,
                center_y,
            )
        )

        self._gizmo_drag = {
            "node": node,
            "mode": self.viewport_tool,
            "handle": handle,
            "before": TransformSnapshot.from_node(
                node
            ),
            "start_mouse_x": float(
                mouse_x
            ),
            "start_mouse_y": float(
                mouse_y
            ),
            "start_world_x": float(
                mouse_world[0]
            ),
            "start_world_y": float(
                mouse_world[1]
            ),
            "pivot_x": float(
                pivot_x
            ),
            "pivot_y": float(
                pivot_y
            ),
            "start_angle": drag_angle_degrees(
                mouse_x,
                mouse_y,
                pivot_x,
                pivot_y,
            ),
        }

        self._gizmo_active_handle = (
            handle
        )

    def _update_gizmo_drag(
        self,
        mouse_x: float,
        mouse_y: float,
    ) -> None:
        drag = self._gizmo_drag

        if drag is None:
            return

        node = drag["node"]

        if not self.document.scene.world.is_alive(
            node.entity
        ):
            self._gizmo_drag = None
            self._gizmo_active_handle = None
            return

        before = drag["before"]
        handle = drag["handle"]
        mode = drag["mode"]

        if mode == GIZMO_MOVE:
            screen_dx = (
                float(mouse_x)
                - drag["start_mouse_x"]
            )

            screen_dy = (
                float(mouse_y)
                - drag["start_mouse_y"]
            )

            world_dx = (
                screen_dx
                / max(
                    self.viewport_state.zoom,
                    1e-9,
                )
            )

            world_dy = (
                screen_dy
                / max(
                    self.viewport_state.zoom,
                    1e-9,
                )
            )

            if handle == "x":
                world_dy = 0.0

            elif handle == "y":
                world_dx = 0.0

            local_dx, local_dy = (
                world_delta_to_local(
                    node,
                    world_dx,
                    world_dy,
                )
            )

            x = before.x + local_dx
            y = before.y + local_dy

            if self.viewport_snap_enabled:
                if handle in {
                    "x",
                    "xy",
                }:
                    x = self._snap_value(
                        x,
                        self.viewport_move_snap,
                    )

                if handle in {
                    "y",
                    "xy",
                }:
                    y = self._snap_value(
                        y,
                        self.viewport_move_snap,
                    )

            node.transform.x = float(
                x
            )
            node.transform.y = float(
                y
            )

        elif mode == GIZMO_ROTATE:
            current_angle = (
                drag_angle_degrees(
                    mouse_x,
                    mouse_y,
                    drag["pivot_x"],
                    drag["pivot_y"],
                )
            )

            delta = (
                current_angle
                - drag["start_angle"]
            )

            rotation = (
                before.rotation
                + delta
            )

            if self.viewport_snap_enabled:
                rotation = self._snap_value(
                    rotation,
                    self.viewport_rotate_snap,
                )

            node.transform.rotation = float(
                rotation
            )

        elif mode == GIZMO_SCALE:
            dx = (
                float(mouse_x)
                - drag["start_mouse_x"]
            )

            dy = (
                float(mouse_y)
                - drag["start_mouse_y"]
            )

            sensitivity = 90.0

            scale_x = before.scale_x
            scale_y = before.scale_y

            if handle == "x":
                scale_x = (
                    before.scale_x
                    + dx / sensitivity
                )

            elif handle == "y":
                scale_y = (
                    before.scale_y
                    + dy / sensitivity
                )

            else:
                uniform_delta = (
                    dx + dy
                ) / (
                    sensitivity * 2.0
                )

                scale_x = (
                    before.scale_x
                    + uniform_delta
                )

                scale_y = (
                    before.scale_y
                    + uniform_delta
                )

            # Keep the first editor scale tool predictable. Negative scale /
            # sprite flipping can still be entered explicitly in Inspector.
            scale_x = max(
                0.01,
                float(scale_x),
            )

            scale_y = max(
                0.01,
                float(scale_y),
            )

            if self.viewport_snap_enabled:
                if handle in {
                    "x",
                    "uniform",
                }:
                    scale_x = self._snap_value(
                        scale_x,
                        self.viewport_scale_snap,
                    )

                if handle in {
                    "y",
                    "uniform",
                }:
                    scale_y = self._snap_value(
                        scale_y,
                        self.viewport_scale_snap,
                    )

                scale_x = max(
                    0.01,
                    scale_x,
                )

                scale_y = max(
                    0.01,
                    scale_y,
                )

            node.transform.scale_x = float(
                scale_x
            )
            node.transform.scale_y = float(
                scale_y
            )

        self.document.mark_dirty()
        self._refresh_inspector()
        self.document_label.text = (
            f"{self.project.name}  |  "
            f"{self.document.title}"
        )

    def _finish_gizmo_drag(
        self,
        *,
        cancel: bool = False,
    ) -> None:
        drag = self._gizmo_drag

        if drag is None:
            return

        node = drag["node"]
        before = drag["before"]

        self._gizmo_drag = None
        self._gizmo_active_handle = None

        if cancel:
            before.apply(
                node
            )

            self._refresh_inspector()
            self.status_label.text = (
                "Transform cancelled"
            )

            return

        after = TransformSnapshot.from_node(
            node
        )

        if after == before:
            return

        mode = drag["mode"]

        label = {
            GIZMO_MOVE: "Move Node",
            GIZMO_ROTATE: "Rotate Node",
            GIZMO_SCALE: "Scale Node",
        }.get(
            mode,
            "Transform Node",
        )

        # The node is already at `after` from live dragging. execute() simply
        # reapplies that value and records exactly one undo/redo operation.
        self.commands.execute(
            TransformNodeCommand(
                node,
                before,
                after,
                label=label,
            )
        )

        self._sync_prefab_instance_overrides(node)
        self.document.mark_dirty()
        self._refresh_document_ui()
        self.status_label.text = (
            label
        )

    def _gizmo_handle_under_mouse(
        self,
        node,
        mouse_x: float,
        mouse_y: float,
    ) -> str | None:
        pivot_x, pivot_y = (
            self._gizmo_pivot_screen(
                node
            )
        )

        return gizmo_hit_test(
            self.viewport_tool,
            mouse_x=mouse_x,
            mouse_y=mouse_y,
            pivot_x=pivot_x,
            pivot_y=pivot_y,
        )

    def _update_viewport_input(self) -> None:
        if self.game.renderer is None:
            return

        if self._any_editor_dialog_open():
            return

        if self._asset_drag_active:
            return

        input_manager = self.game.input

        # Finish a drag even if the pointer leaves the viewport.
        if self._gizmo_drag is not None:
            mouse_x, mouse_y = (
                self._viewport_mouse_centered()
            )

            if input_manager.key_pressed(
                "escape"
            ):
                self._finish_gizmo_drag(
                    cancel=True
                )
                return

            if input_manager.mouse_down(
                "left"
            ):
                self._update_gizmo_drag(
                    mouse_x,
                    mouse_y,
                )

            if input_manager.mouse_released(
                "left"
            ):
                self._finish_gizmo_drag()

            return

        if input_manager.key_pressed("f"):
            self._focus_selected_node()

        if input_manager.key_pressed("home"):
            self.viewport_state.reset()
            self.status_label.text = "Viewport reset"

        if not self._mouse_inside_viewport_canvas():
            self._gizmo_active_handle = None
            return

        center_x, center_y = (
            self.viewport_canvas.calculate_position()
        )

        mouse_x, mouse_y = (
            self._viewport_mouse_centered()
        )

        # ------------------------------------------------------
        # TOOL SHORTCUTS
        # ------------------------------------------------------

        if input_manager.key_pressed(
            "w"
        ):
            self.viewport_tool = (
                GIZMO_MOVE
            )

        if input_manager.key_pressed(
            "e"
        ):
            self.viewport_tool = (
                GIZMO_ROTATE
            )

        if input_manager.key_pressed(
            "r"
        ):
            self.viewport_tool = (
                GIZMO_SCALE
            )

        if input_manager.key_pressed(
            "g"
        ):
            self.viewport_snap_enabled = (
                not self.viewport_snap_enabled
            )

        # ------------------------------------------------------
        # CAMERA
        # ------------------------------------------------------

        if input_manager.mouse_down(
            "middle"
        ):
            delta_x, delta_y = (
                input_manager.mouse_delta
            )

            if delta_x or delta_y:
                self.viewport_state.pan_screen_delta(
                    delta_x,
                    delta_y,
                )

        _wheel_x, wheel_y = (
            input_manager.wheel
        )

        if wheel_y:
            factor = (
                1.15
                ** float(wheel_y)
            )

            self.viewport_state.zoom_at(
                mouse_x,
                mouse_y,
                center_x,
                center_y,
                factor,
            )

        # ------------------------------------------------------
        # GIZMO
        # ------------------------------------------------------

        selected = (
            self._selected_viewport_node()
        )

        handle = None

        if selected is not None:
            handle = (
                self._gizmo_handle_under_mouse(
                    selected,
                    mouse_x,
                    mouse_y,
                )
            )

        self._gizmo_active_handle = (
            handle
        )

        if (
            input_manager.mouse_pressed(
                "left"
            )
            and not input_manager.mouse_down(
                "middle"
            )
        ):
            if (
                selected is not None
                and handle is not None
            ):
                self._begin_gizmo_drag(
                    selected,
                    handle,
                    mouse_x,
                    mouse_y,
                )

            else:
                self._select_node_from_viewport()

        snap_text = (
            "ON"
            if self.viewport_snap_enabled
            else "OFF"
        )

        tool_text = {
            GIZMO_MOVE: "Move",
            GIZMO_ROTATE: "Rotate",
            GIZMO_SCALE: "Scale",
        }.get(
            self.viewport_tool,
            self.viewport_tool,
        )

        self.viewport_controls.text = (
            f"W Move  E Rotate  R Scale  G Snap:{snap_text}   "
            f"F Focus  Home Reset  P Paint  X Erase  B Fill  "
            f"MMB Pan  Wheel Zoom   "
            f"{tool_text}   "
            f"{self.viewport_state.zoom * 100.0:.0f}%"
        )

    # ==========================================================
    # INSPECTOR
    # ==========================================================

    def _build_inspector(self) -> None:
        self.inspector_title = self._panel_title(self.inspector, "Inspector")

        self.inspector_type = self.inspector.create_child(
            "InspectorType",
            node_type=Label,
        )
        self.inspector_type.text = "No node selected"
        self.inspector_type.scale = 0.64
        self.inspector_type.anchor = (0.0, 0.0)
        self.inspector_type.pivot = (0.0, 0.0)

        self.inspector_scroll = self.inspector.create_child(
            "InspectorScroll",
            node_type=ScrollView,
        )
        self.inspector_scroll.background = (0, 0, 0, 0)
        self.inspector_scroll.border_width = 0.0
        self.inspector_scroll.scroll_speed = 48.0

        self._ensure_inspector_controls(
            self.inspector_registry.registered_properties()
        )

        self._refresh_inspector()

    def _ensure_inspector_controls(
        self,
        properties,
    ) -> None:
        """Create Inspector controls lazily for registered property metadata."""

        for prop in properties:
            if prop.group not in self._inspector_groups:
                group_label = self.inspector_scroll.create_content_child(
                    f"InspectorGroup{prop.group.replace(' ', '')}",
                    node_type=Label,
                )
                group_label.text = prop.group
                group_label.scale = 0.68
                group_label.anchor = (0.0, 0.0)
                group_label.pivot = (0.0, 0.0)
                group_label.visible = False

                self._inspector_groups[
                    prop.group
                ] = group_label

            if prop.key in self._inspector_controls:
                continue

            label = self.inspector_scroll.create_content_child(
                f"InspectorLabel{prop.key}",
                node_type=Label,
            )
            label.text = prop.label
            label.scale = 0.60
            label.anchor = (0.0, 0.0)
            label.pivot = (0.0, 0.0)
            label.visible = False

            self._inspector_labels[
                prop.key
            ] = label

            if prop.kind == "bool":
                control = self.inspector_scroll.create_content_child(
                    f"InspectorField{prop.key}",
                    node_type=CheckBox,
                )
                control.text = ""
                control.text_scale = 0.60
                control.box_size = 24.0
                control.on_change = (
                    lambda checked, key=prop.key:
                    self._on_inspector_bool_changed(
                        key,
                        checked,
                    )
                )

            else:
                control = self.inspector_scroll.create_content_child(
                    f"InspectorField{prop.key}",
                    node_type=TextInput,
                )
                control.auto_size = False
                control.on_submit = (
                    lambda text, key=prop.key:
                    self._on_inspector_text_submitted(
                        key,
                        text,
                    )
                )

            control.visible = False
            control.enabled = False

            self._inspector_controls[
                prop.key
            ] = control

    def _selected_inspector_properties(self):
        node = self.selection.selected

        if node is None:
            return ()

        return self.inspector_registry.properties_for(
            node
        )

    def _property_by_key(self, key: str):
        for prop in self._selected_inspector_properties():
            if prop.key == key:
                return prop

        return None

    def _refresh_inspector(self) -> None:
        node = self.selection.selected

        self._inspector_syncing = True

        try:
            if node is None:
                self.inspector_type.text = (
                    "No node selected"
                )

                for label in (
                    self._inspector_labels.values()
                ):
                    label.visible = False

                for group in (
                    self._inspector_groups.values()
                ):
                    group.visible = False

                for control in (
                    self._inspector_controls.values()
                ):
                    control.visible = False
                    control.enabled = False

                return

            self.inspector_type.text = (
                f"{type(node).__name__}  |  "
                f"{len(getattr(node, 'children', ()))} "
                "child(ren)"
            )

            props = (
                self.inspector_registry.properties_for(
                    node
                )
            )

            self._ensure_inspector_controls(
                props
            )

            active_keys = {
                prop.key
                for prop in props
            }

            active_groups = {
                prop.group
                for prop in props
            }

            # --------------------------------------------------
            # RESET VISIBILITY FIRST
            # --------------------------------------------------
            #
            # Controls are reused between different selected node
            # types. Always hide/disable every old control before
            # enabling the properties for the new node. Otherwise
            # stale TextInputs / CheckBoxes can remain visible and
            # overlap the currently active controls.

            for group in (
                self._inspector_groups.values()
            ):
                group.visible = False

            for label in (
                self._inspector_labels.values()
            ):
                label.visible = False

            for control in (
                self._inspector_controls.values()
            ):
                control.visible = False
                control.enabled = False

            # --------------------------------------------------
            # ACTIVE GROUPS / LABELS
            # --------------------------------------------------

            for name, group in (
                self._inspector_groups.items()
            ):
                group.visible = (
                    name in active_groups
                )

            for key, label in (
                self._inspector_labels.items()
            ):
                label.visible = (
                    key in active_keys
                )

            structural_root = (
                node
                is self.document.scene.root
                or node
                is self.document.scene.ui
            )

            # --------------------------------------------------
            # ACTIVE CONTROLS
            # --------------------------------------------------

            for prop in props:
                control = (
                    self._inspector_controls.get(
                        prop.key
                    )
                )

                if control is None:
                    continue

                try:
                    value = (
                        PropertyPathAccessor(
                            node,
                            prop.path,
                        ).get()
                    )

                except (
                    AttributeError,
                    TypeError,
                ):
                    control.visible = False
                    control.enabled = False

                    label = (
                        self._inspector_labels.get(
                            prop.key
                        )
                    )

                    if label is not None:
                        label.visible = False

                    continue

                control.visible = True
                control.enabled = bool(
                    prop.editable
                )

                if (
                    prop.key == "name"
                    and structural_root
                ):
                    control.enabled = False

                # ----------------------------------------------
                # BOOL
                # ----------------------------------------------

                if prop.kind == "bool":
                    control.set_checked(
                        bool(
                            value
                        ),
                        emit=False,
                    )

                # ----------------------------------------------
                # FLOAT
                # ----------------------------------------------

                elif prop.kind == "float":
                    try:
                        text_value = (
                            f"{float(value):.{prop.decimals}f}"
                        )

                    except (
                        TypeError,
                        ValueError,
                    ):
                        text_value = str(
                            value
                        )

                    control.set_text(
                        text_value,
                        emit=False,
                    )

                # ----------------------------------------------
                # INT
                # ----------------------------------------------

                elif prop.kind == "int":
                    try:
                        text_value = str(
                            int(
                                value
                            )
                        )

                    except (
                        TypeError,
                        ValueError,
                    ):
                        text_value = str(
                            value
                        )

                    control.set_text(
                        text_value,
                        emit=False,
                    )

                # ----------------------------------------------
                # TEXT
                # ----------------------------------------------

                else:
                    control.set_text(
                        str(
                            value
                        ),
                        emit=False,
                    )

        finally:
            self._inspector_syncing = False

    def _parse_inspector_value(
        self,
        prop,
        text: str,
    ):
        if prop.kind == "float":
            value = str(text).strip().replace(
                ",",
                ".",
            )

            if not value:
                raise ValueError(
                    f"{prop.label} cannot be empty."
                )

            return float(value)

        if prop.kind == "int":
            value = str(text).strip()

            if not value:
                raise ValueError(
                    f"{prop.label} cannot be empty."
                )

            # base=0 allows convenient decimal and 0x... masks.
            return int(
                value,
                0,
            )

        value = str(text)

        if (
            prop.key == "name"
            and not value.strip()
        ):
            raise ValueError(
                "Node name cannot be empty."
            )

        if prop.key == "name":
            return value.strip()

        return value

    def _apply_inspector_property(
        self,
        prop,
        value,
    ) -> None:
        node = self.selection.selected

        if node is None:
            return

        if (
            prop.key == "name"
            and (
                node is self.document.scene.root
                or node is self.document.scene.ui
            )
        ):
            self._refresh_inspector()
            return

        accessor = PropertyPathAccessor(
            node,
            prop.path,
        )

        try:
            current = accessor.get()
        except (AttributeError, TypeError) as exc:
            self._show_error(
                f"Could not read {prop.label}:\n{exc}"
            )
            return

        if current == value:
            self._refresh_inspector()
            return

        try:
            self.commands.execute(
                SetPropertyCommand(
                    node,
                    prop.path,
                    value,
                    label=(
                        f"Set {getattr(node, 'name', type(node).__name__)} "
                        f"{prop.label}"
                    ),
                )
            )
        except Exception as exc:
            self._show_error(
                f"Could not set {prop.label}:\n{exc}"
            )
            self._refresh_inspector()
            return

        self._sync_prefab_instance_overrides(node)
        self.document.mark_dirty()

        if prop.key == "name":
            self._refresh_scene_tree()

        self._refresh_inspector()

        self.document_label.text = (
            f"{self.project.name}  |  {self.document.title}"
        )

        self.status_label.text = (
            f"Changed {prop.label}"
        )

    def _on_inspector_text_submitted(
        self,
        key: str,
        text: str,
    ) -> None:
        if self._inspector_syncing:
            return

        prop = self._property_by_key(
            key
        )

        if prop is None:
            return

        try:
            value = self._parse_inspector_value(
                prop,
                text,
            )
        except ValueError as exc:
            self.status_label.text = str(exc)
            self._refresh_inspector()
            return

        self._apply_inspector_property(
            prop,
            value,
        )

    def _on_inspector_bool_changed(
        self,
        key: str,
        checked: bool,
    ) -> None:
        if self._inspector_syncing:
            return

        prop = self._property_by_key(
            key
        )

        if prop is None:
            return

        self._apply_inspector_property(
            prop,
            bool(checked),
        )

    def _on_selection_changed(self, node, _previous) -> None:
        self._refresh_inspector()
        self._refresh_animation_panel()

        # Reset only after the selected node's controls have been made
        # visible and the ScrollView content size has been recalculated.
        # Otherwise the old scroll offset can survive the selection change.
        if hasattr(self, "inspector_scroll"):
            self._sync_inspector_layout(
                float(self.inspector.size[0]),
                float(self.inspector.size[1]),
            )
            self.inspector_scroll.set_scroll_y(
                0.0,
                emit=False,
            )

        if node is None:
            self.status_label.text = "Selection cleared"
            return

        self.status_label.text = (
            f"Selected {getattr(node, 'name', type(node).__name__)}"
        )

    # ==========================================================
    # BOTTOM DOCK
    # ==========================================================

    def _build_bottom_dock(self) -> None:
        self.assets_button = self._button(
            self.bottom_dock,
            "AssetsTab",
            "Assets",
            lambda: self._set_bottom_tab(
                "assets"
            ),
        )

        self.console_button = self._button(
            self.bottom_dock,
            "ConsoleTab",
            "Console",
            lambda: self._set_bottom_tab(
                "console"
            ),
        )

        self.animation_button = self._button(
            self.bottom_dock,
            "AnimationTab",
            "Animation",
            lambda: self._set_bottom_tab(
                "animation"
            ),
        )

        self.bottom_title = (
            self.bottom_dock.create_child(
                "BottomTitle",
                node_type=Label,
            )
        )

        self.bottom_title.text = (
            "Assets"
        )
        self.bottom_title.scale = 0.78
        self.bottom_title.anchor = (
            0.0,
            0.0,
        )
        self.bottom_title.pivot = (
            0.0,
            0.0,
        )

        # ------------------------------------------------------
        # Assets toolbar
        # ------------------------------------------------------

        self.asset_up_button = self._button(
            self.bottom_dock,
            "AssetUpButton",
            "Up",
            self._asset_go_up,
        )

        self.asset_refresh_button = self._button(
            self.bottom_dock,
            "AssetRefreshButton",
            "Refresh",
            self._refresh_asset_browser,
        )

        self.asset_search = (
            self.bottom_dock.create_child(
                "AssetSearch",
                node_type=TextInput,
            )
        )

        self.asset_search.placeholder = (
            "Search assets..."
        )
        self.asset_search.text_scale = 0.62
        self.asset_search.auto_size = False
        self.asset_search.on_change = (
            self._on_asset_search_changed
        )

        self.asset_path_label = (
            self.bottom_dock.create_child(
                "AssetPath",
                node_type=Label,
            )
        )

        self.asset_path_label.scale = 0.58
        self.asset_path_label.anchor = (
            0.0,
            0.0,
        )
        self.asset_path_label.pivot = (
            0.0,
            0.0,
        )

        # ------------------------------------------------------
        # Asset list
        # ------------------------------------------------------

        self.asset_list = (
            self.bottom_dock.create_child(
                "AssetList",
                node_type=ListView,
            )
        )

        self.asset_list.item_height = 28.0
        self.asset_list.spacing = 1.0
        self.asset_list.padding_left = 5.0
        self.asset_list.padding_right = 5.0
        self.asset_list.padding_top = 5.0
        self.asset_list.padding_bottom = 5.0
        self.asset_list.text_padding_left = 7.0
        self.asset_list.text_scale = 0.58
        self.asset_list.on_change = (
            self._on_asset_selected
        )
        self.asset_list.on_activate = (
            self._on_asset_activated
        )

        # ------------------------------------------------------
        # Preview / details
        # ------------------------------------------------------

        self.asset_preview = (
            self.bottom_dock.create_child(
                "AssetPreview",
                node_type=AssetPreview,
            )
        )

        if self.game.engine is not None:
            self.asset_preview.asset_manager = (
                self.game.engine.assets
            )

        self.asset_details = (
            self.bottom_dock.create_child(
                "AssetDetails",
                node_type=Label,
            )
        )

        self.asset_details.scale = 0.55
        self.asset_details.anchor = (
            0.0,
            0.0,
        )
        self.asset_details.pivot = (
            0.0,
            0.0,
        )

        # ------------------------------------------------------
        # Console output
        # ------------------------------------------------------

        self.console_content = (
            self.bottom_dock.create_child(
                "ConsoleContent",
                node_type=Label,
            )
        )

        self.console_content.text = "Console ready."
        self.console_content.scale = 0.66
        self.console_content.anchor = (
            0.0,
            0.0,
        )
        self.console_content.pivot = (
            0.0,
            0.0,
        )

        self.console_clear_button = self._button(
            self.bottom_dock,
            "ConsoleClearButton",
            "Clear",
            self._clear_editor_console,
        )

        self.animation_list = self.bottom_dock.create_child(
            "AnimationList",
            node_type=ListView,
        )
        self.animation_list.item_height = 30.0
        self.animation_list.spacing = 1.0
        self.animation_list.padding_left = 5.0
        self.animation_list.padding_right = 5.0
        self.animation_list.padding_top = 5.0
        self.animation_list.padding_bottom = 5.0
        self.animation_list.text_padding_left = 7.0
        self.animation_list.text_scale = 0.58
        self.animation_list.on_change = self._on_animation_selected

        self.animation_frame_list = self.bottom_dock.create_child(
            "AnimationFrameList",
            node_type=ListView,
        )
        self.animation_frame_list.item_height = 30.0
        self.animation_frame_list.spacing = 1.0
        self.animation_frame_list.padding_left = 5.0
        self.animation_frame_list.padding_right = 5.0
        self.animation_frame_list.padding_top = 5.0
        self.animation_frame_list.padding_bottom = 5.0
        self.animation_frame_list.text_padding_left = 7.0
        self.animation_frame_list.text_scale = 0.58

        self.animation_new_button = self._button(
            self.bottom_dock,
            "AnimationNew",
            "New",
            self._add_animation_clip,
        )

        self.animation_status_label = self.bottom_dock.create_child(
            "AnimationStatus",
            node_type=Label,
        )
        self.animation_status_label.scale = 0.58
        self.animation_status_label.anchor = (0.0, 0.0)
        self.animation_status_label.pivot = (0.0, 0.0)

        self.animation_play_button = self._button(
            self.bottom_dock,
            "AnimationPlay",
            "Play",
            self._play_selected_animation,
        )
        self.animation_pause_button = self._button(
            self.bottom_dock,
            "AnimationPause",
            "Pause",
            self._pause_selected_animation,
        )
        self.animation_stop_button = self._button(
            self.bottom_dock,
            "AnimationStop",
            "Stop",
            self._stop_selected_animation,
        )
        self.animation_speed_input = self.bottom_dock.create_child(
            "AnimationSpeed",
            node_type=TextInput,
        )
        self.animation_speed_input.placeholder = "Speed"
        self.animation_speed_input.auto_size = False
        self.animation_speed_input.on_submit = self._on_animation_speed_submitted

        # ------------------------------------------------------
        # Context actions
        # ------------------------------------------------------

        self.asset_context = (
            self.bottom_dock.create_child(
                "AssetContextMenu",
                node_type=Panel,
            )
        )

        self.asset_context.background = (
            28,
            30,
            34,
            255,
        )
        self.asset_context.border_color = (
            70,
            74,
            80,
            255,
        )
        self.asset_context.border_width = 1.0
        self.asset_context.visible = False

        self.asset_context_open = self._button(
            self.asset_context,
            "ContextOpen",
            "Open",
            self._asset_context_open_selected,
        )

        self.asset_context_reveal = self._button(
            self.asset_context,
            "ContextReveal",
            "Reveal",
            self._asset_context_reveal_selected,
        )

        self.asset_context_refresh = self._button(
            self.asset_context,
            "ContextRefresh",
            "Refresh",
            self._refresh_asset_browser,
        )

        # Do not refresh here yet:
        # _build_bottom_dock() runs before _build_status_bar(), so the
        # status_label does not exist at this point. The normal
        # _refresh_document_ui() call at the end of _build_ui() refreshes
        # the asset browser once every editor UI node has been created.
        self._apply_bottom_tab_visibility()

    def _build_asset_drag_overlay(self) -> None:
        self.asset_drag_badge = self.ui.create_child("AssetDragBadge", node_type=Panel)
        self.asset_drag_badge.size = (220.0, 34.0)
        self.asset_drag_badge.anchor = (0.5, 0.5); self.asset_drag_badge.pivot = (0.5, 0.5)
        self.asset_drag_badge.background = (30, 33, 38, 245); self.asset_drag_badge.border_color = (80, 120, 190, 255)
        self.asset_drag_badge.border_width = 1.0; self.asset_drag_badge.border_radius = 5.0; self.asset_drag_badge.visible = False
        self.asset_drag_label = self.asset_drag_badge.create_child("AssetDragLabel", node_type=Label)
        self.asset_drag_label.anchor = (0.5, 0.5); self.asset_drag_label.pivot = (0.5, 0.5); self.asset_drag_label.scale = 0.58

    # ==========================================================
    # STATUS
    # ==========================================================

    def _build_status_bar(self) -> None:
        self.status_label = self.status_bar.create_child(
            "StatusLabel",
            node_type=Label,
        )
        self.status_label.text = "Ready"
        self.status_label.scale = 0.62
        self.status_label.anchor = (0.0, 0.5)
        self.status_label.pivot = (0.0, 0.5)

        self.engine_label = self.status_bar.create_child(
            "EngineLabel",
            node_type=Label,
        )
        self.engine_label.text = "Nexora Editor v0.10"
        self.engine_label.scale = 0.62
        self.engine_label.anchor = (1.0, 0.5)
        self.engine_label.pivot = (1.0, 0.5)

    # ==========================================================
    # REFRESH
    # ==========================================================

    def _refresh_document_ui(self) -> None:
        self._refresh_scene_tree()
        self._refresh_inspector()
        self._refresh_animation_panel()
        self.document_label.text = (
            f"{self.project.name}  |  {self.document.title}"
        )
        self.viewport_subtitle.text = (
            f"Editing: {self.document.display_name}"
        )
        self._refresh_asset_summary()
        if hasattr(self, "undo_button"):
            self.undo_button.text = "Undo"
            self.redo_button.text = "Redo"

    def _refresh_asset_summary(self) -> None:
        # Kept as the document-workflow refresh hook.
        self._refresh_asset_browser(
            preserve_selection=True
        )

    def _refresh_asset_browser(
        self,
        preserve_selection: bool = True,
    ) -> None:
        if not hasattr(
            self,
            "asset_list",
        ):
            return

        selected_path = (
            self._selected_asset.path
            if (
                preserve_selection
                and self._selected_asset
                is not None
            )
            else None
        )

        self._asset_entries = (
            self.asset_browser.refresh()
        )

        self.asset_list.set_items(
            [
                entry.display_name
                for entry
                in self._asset_entries
            ]
        )

        self.asset_path_label.text = (
            f"Project / "
            f"{self.asset_browser.relative_directory}"
        )

        self.asset_up_button.enabled = (
            self.asset_browser.can_go_up
        )

        restored = False

        if selected_path is not None:
            for index, entry in enumerate(
                self._asset_entries
            ):
                if (
                    entry.path
                    == selected_path
                ):
                    self.asset_list.set_selected_index(
                        index,
                        emit=False,
                    )

                    self._set_selected_asset(
                        entry
                    )

                    restored = True
                    break

        if not restored:
            self.asset_list.selected_index = -1
            self._set_selected_asset(
                None
            )

        self.status_label.text = (
            f"Assets: "
            f"{len(self._asset_entries)} item(s)"
        )

    def _on_asset_search_changed(
        self,
        text: str,
    ) -> None:
        self.asset_browser.set_search(
            text
        )

        self._refresh_asset_browser(
            preserve_selection=False
        )

    def _asset_go_up(self) -> None:
        self.asset_browser.go_up()
        self.asset_search.set_text(
            "",
            emit=False,
        )
        self.asset_browser.search_text = ""
        self._refresh_asset_browser(
            preserve_selection=False
        )

    def _set_selected_asset(
        self,
        entry,
    ) -> None:
        self._selected_asset = entry

        self._asset_drag_payload = (
            None
            if entry is None
            else entry.drag_payload
        )

        if entry is None:
            self.asset_preview.set_asset(
                None
            )

            self.asset_details.text = (
                "Select an asset.\n"
                "Double-click folders/scenes to open."
            )

            return

        if entry.kind == "image":
            self.asset_preview.set_asset(
                entry.path
            )

        else:
            self.asset_preview.set_asset(
                None
            )

        if entry.is_directory:
            size_text = "Folder"

        else:
            size_text = format_file_size(
                entry.size_bytes
            )

        self.asset_details.text = (
            f"{entry.name}\n"
            f"Type: {entry.kind}\n"
            f"Size: {size_text}\n"
            f"{entry.relative_path}"
        )

    def _on_asset_selected(
        self,
        index: int,
        _label: str | None,
    ) -> None:
        entry = (
            self.asset_browser.entry_at(
                index
            )
        )

        self._set_selected_asset(
            entry
        )

        if entry is None:
            return

        self.status_label.text = (
            f"Selected asset: "
            f"{entry.relative_path}"
        )

    def _activate_scene_asset(
        self,
        path: Path,
    ) -> None:
        def do_open() -> None:
            self._on_open_scene_selected(
                self.open_scene_dialog,
                path,
            )

        self._run_after_dirty_check(
            do_open
        )

    def _on_asset_activated(
        self,
        index: int,
        _label: str,
    ) -> None:
        entry = (
            self.asset_browser.entry_at(
                index
            )
        )

        if entry is None:
            return

        if entry.is_directory:
            try:
                self.asset_browser.navigate(
                    entry.path
                )

            except Exception as exc:
                self._show_error(
                    "Could not open folder:\n"
                    f"{exc}"
                )
                return

            self.asset_search.set_text(
                "",
                emit=False,
            )
            self.asset_browser.search_text = ""
            self._refresh_asset_browser(
                preserve_selection=False
            )

            return

        if entry.kind == "scene":
            self._activate_scene_asset(
                entry.path
            )
            return

        if entry.kind == "prefab":
            self.status_label.text = (
                "Prefab selected. "
                "Drag it into the viewport to instantiate it."
            )
            return

        if entry.kind == "tilemap":
            self._assign_tilemap_asset(entry.path)
            return

        if entry.kind == "image":
            self.status_label.text = (
                f"Previewing {entry.name}"
            )
            return

        self.status_label.text = (
            f"Asset: {entry.relative_path}"
        )

    def _assign_tilemap_asset(self, path: Path) -> None:
        """Bind a standalone TileMap asset to the selected TileMapNode."""
        node = self.selection.selected
        if not isinstance(node, TileMapNode):
            self.status_label.text = "Select a TileMapNode before opening a TileMap asset."
            return

        engine = self.game.engine
        assets = getattr(engine, "assets", None)
        if assets is None:
            self._show_error("The engine asset manager is not available.")
            return

        try:
            relative_path = path.resolve().relative_to(Path(assets.root).resolve()).as_posix()
            self.commands.execute(
                TileMapAssetCommand(node, relative_path, assets)
            )
        except ValueError:
            self._show_error("The TileMap asset must be inside the project's assets folder.")
            return
        except Exception as exc:
            self._show_error(f"Could not load TileMap asset:\n{exc}")
            return

        self.document.mark_dirty()
        self._refresh_inspector()
        self._refresh_scene_tree()
        self.status_label.text = f"Assigned TileMap: {relative_path}"

    def _unique_node_name(self, base_name: str) -> str:
        base = str(base_name).strip() or "Sprite"
        existing = {str(node.name) for node in self._iter_viewport_nodes()}
        if base not in existing: return base
        index = 2
        while f"{base}_{index}" in existing: index += 1
        return f"{base}_{index}"

    def _sync_prefab_instance_overrides(self, node=None) -> None:
        """Keep a prefab instance's saved root state in sync with edits."""

        node = self.selection.selected if node is None else node

        if node is None or not getattr(node, "_nexora_prefab_source", None):
            return

        try:
            node._nexora_prefab_overrides = (
                prefab_instance_overrides_for_node(
                    node,
                    self.game.scene_serializer.registry,
                )
            )
        except Exception:
            # The instance was created by the registered prefab serializer, so
            # this should only be reachable for a custom runtime node that was
            # changed outside the editor registry. Saving can still report the
            # original serialization error normally.
            return

    def _sync_all_prefab_instance_overrides(self) -> None:
        for node in self._iter_viewport_nodes():
            self._sync_prefab_instance_overrides(node)

    def _drop_image_asset_in_viewport(self, entry, mouse_x: float, mouse_y: float) -> None:
        if entry is None or entry.kind != "image" or self.game.engine is None: return
        center_x, center_y = self.viewport_canvas.calculate_position()
        world_x, world_y = self.viewport_state.screen_to_world(mouse_x, mouse_y, center_x, center_y)
        name = self._unique_node_name(entry.path.stem)
        command = AddImageSpriteCommand(parent=self.document.scene.root, registry=self.game.scene_serializer.registry, assets=self.game.engine.assets, asset_path=entry.path, name=name, x=world_x, y=world_y, context=self._serialization_context())
        try:
            node = self.commands.execute(command)
        except Exception as exc:
            self._show_error(f"Could not create sprite from asset:\n{exc}"); return
        self.document.mark_dirty(); self.selection.select(node); self._refresh_document_ui()
        self.status_label.text = f"Created sprite '{name}' from {entry.name}"

    def _drop_prefab_asset_in_viewport(self, entry, mouse_x: float, mouse_y: float) -> None:
        if entry is None or entry.kind != "prefab":
            return

        center_x, center_y = self.viewport_canvas.calculate_position()
        world_x, world_y = self.viewport_state.screen_to_world(
            mouse_x,
            mouse_y,
            center_x,
            center_y,
        )
        name = self._unique_node_name(entry.path.stem)
        serializer = self.game.scene_serializer
        command = InstantiatePrefabCommand(
            parent=self.document.scene.root,
            prefab_serializer=serializer.prefabs,
            registry=serializer.registry,
            prefab_path=entry.path,
            name=name,
            x=world_x,
            y=world_y,
            context=self._serialization_context(),
        )

        try:
            node = self.commands.execute(command)
        except Exception as exc:
            self._show_error(
                f"Could not instantiate prefab:\n{exc}"
            )
            return

        self.document.mark_dirty()
        self.selection.select(node)
        self._refresh_document_ui()
        self.status_label.text = (
            f"Instantiated prefab '{name}' from {entry.name}"
        )

    def _reset_asset_drag(self) -> None:
        self._asset_pointer_press = None; self._asset_drag_active = False; self._asset_drag_entry = None
        if hasattr(self, "asset_drag_badge"): self.asset_drag_badge.visible = False

    def _update_asset_drag_input(self) -> None:
        if self._bottom_tab != "assets" or self._any_editor_dialog_open(): self._reset_asset_drag(); return
        input_manager = self.game.input
        mouse_x, mouse_y = self._viewport_mouse_centered()
        if self._asset_pointer_press is None and input_manager.mouse_pressed("left"):
            hovered = self.asset_list.hovered_index
            if 0 <= hovered < len(self._asset_entries):
                entry = self._asset_entries[hovered]
                if not entry.is_directory and entry.kind in {"image", "prefab"}:
                    self._asset_pointer_press = (mouse_x, mouse_y); self._asset_drag_entry = entry
        if self._asset_pointer_press is not None and input_manager.mouse_down("left"):
            sx, sy = self._asset_pointer_press; dx = mouse_x-sx; dy = mouse_y-sy
            if not self._asset_drag_active and dx*dx+dy*dy >= self._asset_drag_threshold*self._asset_drag_threshold: self._asset_drag_active = True
            if self._asset_drag_active:
                entry = self._asset_drag_entry; self.asset_drag_badge.visible = True; self.asset_drag_badge.position = (mouse_x+118.0, mouse_y+24.0)
                target = "Image -> Sprite" if entry.kind == "image" else "Prefab -> Instance"
                self.asset_drag_label.text = f"Drop {target}  |  {entry.name}"
                self.asset_drag_badge.border_color = (70,190,110,255) if self._mouse_inside_viewport_canvas() else (80,120,190,255)
        if self._asset_pointer_press is not None and input_manager.mouse_released("left"):
            entry = self._asset_drag_entry; should_drop = self._asset_drag_active and self._mouse_inside_viewport_canvas()
            self._reset_asset_drag()
            if not should_drop:
                return
            if entry.kind == "image":
                self._drop_image_asset_in_viewport(entry, mouse_x, mouse_y)
            elif entry.kind == "prefab":
                self._drop_prefab_asset_in_viewport(entry, mouse_x, mouse_y)

    def _asset_context_open_selected(
        self,
    ) -> None:
        entry = self._selected_asset

        if entry is None:
            return

        try:
            index = (
                self._asset_entries.index(
                    entry
                )
            )

        except ValueError:
            return

        self._on_asset_activated(
            index,
            entry.display_name,
        )

        self.asset_context.visible = False

    def _asset_context_reveal_selected(
        self,
    ) -> None:
        entry = self._selected_asset

        if entry is None:
            return

        try:
            reveal_in_file_manager(
                entry.path
            )

        except Exception as exc:
            self._show_error(
                "Could not reveal asset:\n"
                f"{exc}"
            )

        self.asset_context.visible = False

    def _update_asset_context_input(
        self,
    ) -> None:
        if self._bottom_tab != "assets":
            self.asset_context.visible = False
            return

        input_manager = self.game.input

        if input_manager.mouse_pressed(
            "right"
        ):
            hovered = (
                self.asset_list.hovered_index
            )

            if (
                0
                <= hovered
                < len(self._asset_entries)
            ):
                self.asset_list.set_selected_index(
                    hovered
                )

                self._set_selected_asset(
                    self._asset_entries[
                        hovered
                    ]
                )

                self.asset_context.visible = True

            else:
                self.asset_context.visible = False

        elif (
            input_manager.mouse_pressed(
                "left"
            )
            and self.asset_context.visible
            and self.asset_list.hovered_index >= 0
        ):
            self.asset_context.visible = False

    @property
    def asset_drag_payload(self):
        """Selected asset payload for viewport and inspector drop targets."""
        return self._asset_drag_payload

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

    def _apply_bottom_tab_visibility(
        self,
    ) -> None:
        assets_visible = (
            self._bottom_tab
            == "assets"
        )
        animation_visible = self._bottom_tab == "animation"

        for node in (
            self.asset_up_button,
            self.asset_refresh_button,
            self.asset_search,
            self.asset_path_label,
            self.asset_list,
            self.asset_preview,
            self.asset_details,
        ):
            node.visible = (
                assets_visible
            )

        self.console_content.visible = self._bottom_tab == "console"
        self.console_clear_button.visible = (
            not assets_visible
        )

        for node in (
            self.animation_list,
            self.animation_frame_list,
            self.animation_new_button,
            self.animation_status_label,
            self.animation_play_button,
            self.animation_pause_button,
            self.animation_stop_button,
            self.animation_speed_input,
        ):
            node.visible = animation_visible

        self.console_clear_button.visible = (
            self._bottom_tab == "console"
        )

        if not assets_visible:
            self.asset_context.visible = False

    def _set_bottom_tab(
        self,
        tab: str,
    ) -> None:
        if tab == "console":
            self._bottom_tab = "console"
            self.bottom_title.text = (
                "Console"
            )
            self._apply_bottom_tab_visibility()
            self.status_label.text = (
                "Console panel selected"
            )
            return

        if tab == "animation":
            self._bottom_tab = "animation"
            self.bottom_title.text = "Animation Editor"
            self._apply_bottom_tab_visibility()
            self._refresh_animation_panel()
            self.status_label.text = "Animation editor selected"
            return

        self._bottom_tab = "assets"
        self.bottom_title.text = (
            "Assets"
        )
        self._apply_bottom_tab_visibility()
        self._refresh_asset_browser()
        self.status_label.text = (
            "Assets panel selected"
        )

    def _refresh_console_output(self) -> None:
        engine = getattr(self.game, "engine", None)
        console = getattr(engine, "console", None)
        if console is None:
            text = "No engine console available."
        else:
            lines = getattr(console, "lines", ())
            recent = tuple(lines)[-8:]
            text = "\n".join(
                getattr(line, "display_text", str(line))
                for line in recent
            ) or "Console ready."

        if self.console_content.text != text:
            self.console_content.text = text

    def _clear_editor_console(self) -> None:
        engine = getattr(self.game, "engine", None)
        console = getattr(engine, "console", None)
        if console is not None:
            console.clear()
        self._refresh_console_output()
        self.status_label.text = "Console cleared"

    def _toggle_play_mode(self) -> None:
        if self.game.play_mode:
            self.game.stop_play_mode()
        else:
            self.game.start_play_mode()

    def _open_tilemap_editor(self) -> None:
        """Launch the dedicated TileMap editor for this project."""
        import subprocess
        import sys

        command = [
            sys.executable,
            "-m",
            "nexora",
            "--tilemapedit",
            str(self.project_path),
        ]
        selected = self.selection.selected
        tilemap_asset = getattr(selected, "tilemap_asset", None)
        if tilemap_asset:
            command.extend(("--tilemap", str(tilemap_asset)))

        try:
            subprocess.Popen(command, cwd=str(self.project_path))
            self.status_label.text = "TileMap Editor gestartet"
        except OSError as exc:
            self._show_error(f"Could not start TileMap Editor:\n{exc}")

    # ==========================================================
    # LAYOUT
    # ==========================================================

    def update(self, delta_time: float) -> None:
        super().update(delta_time)
        self._sync_layout()
        self._refresh_console_output()
        animation_node = self._selected_animation_player()
        if (
            self._bottom_tab == "animation"
            and animation_node is not None
            and animation_node.playing
        ):
            animation_node.update(delta_time)
            self._refresh_animation_panel()
        self._update_viewport_input()
        self._update_asset_drag_input()
        self._update_asset_context_input()
        if getattr(self.add_node_dialog, "is_open", False):
            self._sync_add_node_dialog_layout()

    def render(self, renderer) -> None:
        self._sync_layout()
        super().render(renderer)

    def _sync_layout(self) -> None:
        renderer = self.game.renderer

        if renderer is None:
            return

        width = float(renderer.width)
        height = float(renderer.height)

        size = (width, height)
        if size == self._last_size:
            return
        self._last_size = size

        self.background.size = size
        self.background.anchor = (0.5, 0.5)
        self.background.pivot = (0.5, 0.5)

        self.toolbar.anchor = (0.5, 0.0)
        self.toolbar.pivot = (0.5, 0.0)
        self.toolbar.size = (width, self.TOOLBAR_HEIGHT)
        self.toolbar.position = (0.0, self.TOOLBAR_HEIGHT / 2.0)

        self.status_bar.anchor = (0.5, 1.0)
        self.status_bar.pivot = (0.5, 1.0)
        self.status_bar.size = (width, self.STATUS_HEIGHT)
        self.status_bar.position = (0.0, -self.STATUS_HEIGHT / 2.0)

        body_top = self.TOOLBAR_HEIGHT + self.GAP
        body_bottom = height - self.STATUS_HEIGHT - self.GAP
        body_height = max(0.0, body_bottom - body_top)
        bottom_h = min(self.BOTTOM_HEIGHT, max(100.0, body_height * 0.28))
        upper_h = max(0.0, body_height - bottom_h - self.GAP)

        left_w = min(self.LEFT_WIDTH, width * 0.25)
        right_w = min(self.RIGHT_WIDTH, width * 0.3)
        center_w = max(0.0, width - left_w - right_w - self.GAP * 2.0)

        self.scene_tree.anchor = (0.0, 0.0)
        self.scene_tree.pivot = (0.0, 0.0)
        self.scene_tree.size = (left_w, upper_h)
        self.scene_tree.position = (left_w / 2.0, body_top + upper_h / 2.0)

        self.viewport.anchor = (0.0, 0.0)
        self.viewport.pivot = (0.0, 0.0)
        self.viewport.size = (center_w, upper_h)
        self.viewport.position = (
            left_w + self.GAP + center_w / 2.0,
            body_top + upper_h / 2.0,
        )

        self.inspector.anchor = (0.0, 0.0)
        self.inspector.pivot = (0.0, 0.0)
        self.inspector.size = (right_w, upper_h)
        self.inspector.position = (
            left_w + self.GAP + center_w + self.GAP + right_w / 2.0,
            body_top + upper_h / 2.0,
        )

        self.bottom_dock.anchor = (0.0, 0.0)
        self.bottom_dock.pivot = (0.0, 0.0)
        self.bottom_dock.size = (width, bottom_h)
        self.bottom_dock.position = (
            width / 2.0,
            body_top + upper_h + self.GAP + bottom_h / 2.0,
        )

        self._sync_toolbar_layout(width)
        self._sync_scene_tree_layout(left_w, upper_h)
        self._sync_viewport_layout(center_w, upper_h)
        self._sync_inspector_layout(right_w, upper_h)
        self._sync_bottom_layout(width, bottom_h)
        self._sync_status_layout(width)

    def _sync_toolbar_layout(self, width: float) -> None:
        self.brand_label.position = (16.0, 0.0)

        buttons = [
            (self.new_button, 66.0),
            (self.open_button, 74.0),
            (self.save_button, 72.0),
            (self.save_as_button, 92.0),
            (self.save_prefab_button, 82.0),
            (self.undo_button, 72.0),
            (self.redo_button, 72.0),
            (self.play_button, 66.0),
            (self.tilemap_editor_button, 122.0),
        ]
        x = 105.0
        gap = 6.0
        for button, button_width in buttons:
            button.size = (button_width, 34.0)
            button.anchor = (0.0, 0.5)
            button.pivot = (0.5, 0.5)
            button.position = (x + button_width / 2.0, 0.0)
            x += button_width + gap

        self.document_label.position = (-16.0, 0.0)

    def _sync_scene_tree_layout(self, width: float, height: float) -> None:
        # Keep the panel title on its own row. The old layout positioned the
        # buttons from the right edge using non-centred pivots, while Panel
        # rendering itself is centre-based. That made the Delete button draw
        # outside the panel and made its hit box disagree with the pixels.
        self.scene_title.position = (12.0, 10.0)

        button_y = 52.0
        margin = 8.0
        gap = 6.0

        add_w = 34.0
        rename_w = 74.0
        delete_w = 74.0

        total_w = add_w + rename_w + delete_w + gap * 2.0
        start_x = max(margin, (width - total_w) * 0.5)

        self.add_node_button.size = (add_w, 28.0)
        self.add_node_button.anchor = (0.0, 0.0)
        self.add_node_button.pivot = (0.5, 0.5)
        self.add_node_button.position = (
            start_x + add_w / 2.0,
            button_y,
        )

        rename_x = start_x + add_w + gap
        self.rename_node_button.size = (rename_w, 28.0)
        self.rename_node_button.anchor = (0.0, 0.0)
        self.rename_node_button.pivot = (0.5, 0.5)
        self.rename_node_button.position = (
            rename_x + rename_w / 2.0,
            button_y,
        )

        delete_x = rename_x + rename_w + gap
        self.delete_node_button.size = (delete_w, 28.0)
        self.delete_node_button.anchor = (0.0, 0.0)
        self.delete_node_button.pivot = (0.5, 0.5)
        self.delete_node_button.position = (
            delete_x + delete_w / 2.0,
            button_y,
        )

        list_top = 76.0
        self.scene_list.anchor = (0.5, 0.0)
        self.scene_list.pivot = (0.5, 0.5)
        self.scene_list.size = (
            max(0.0, width - 16.0),
            max(0.0, height - list_top - 8.0),
        )
        self.scene_list.position = (
            0.0,
            list_top + self.scene_list.size[1] / 2.0,
        )

    def _sync_viewport_layout(self, width: float, height: float) -> None:
        self.viewport_title.position = (12.0, 10.0)

        header_height = 74.0
        margin = 5.0
        canvas_width = max(0.0, width - margin * 2.0)
        canvas_height = max(0.0, height - header_height - margin)

        self.viewport_canvas.anchor = (0.5, 0.0)
        self.viewport_canvas.pivot = (0.5, 0.5)
        self.viewport_canvas.size = (
            canvas_width,
            canvas_height,
        )
        self.viewport_canvas.position = (
            0.0,
            header_height + canvas_height / 2.0,
        )

        self.viewport_hint.position = (0.0, 0.0)

        self.viewport_subtitle.text = (
            f"Editing: {self.document.display_name}"
        )
        self.viewport_subtitle.position = (
            118.0,
            11.0,
        )

        snap_text = (
            "ON"
            if self.viewport_snap_enabled
            else "OFF"
        )

        tool_text = {
            GIZMO_MOVE: "Move",
            GIZMO_ROTATE: "Rotate",
            GIZMO_SCALE: "Scale",
        }.get(
            self.viewport_tool,
            self.viewport_tool,
        )

        self.viewport_controls.text = (
            f"W Move  E Rotate  R Scale  G Snap:{snap_text}   "
            f"MMB Pan  Wheel Zoom   "
            f"{tool_text}   "
            f"{self.viewport_state.zoom * 100.0:.0f}%"
        )
        self.viewport_controls.position = (
            -12.0,
            11.0,
        )

    def _sync_inspector_layout(self, width: float, height: float) -> None:
        self.inspector_title.position = (12.0, 10.0)
        self.inspector_type.position = (12.0, 39.0)

        scroll_top = 68.0
        scroll_margin = 6.0

        scroll_width = max(
            0.0,
            width - scroll_margin * 2.0,
        )

        scroll_height = max(
            0.0,
            height - scroll_top - scroll_margin,
        )

        self.inspector_scroll.anchor = (0.5, 0.0)
        self.inspector_scroll.pivot = (0.5, 0.5)
        self.inspector_scroll.size = (
            scroll_width,
            scroll_height,
        )
        self.inspector_scroll.position = (
            0.0,
            scroll_top + scroll_height / 2.0,
        )

        label_x = 8.0

        # Leave a little room on the right for the ScrollView edge /
        # scrollbar so TextInputs never touch or exceed the panel border.
        field_x = max(
            104.0,
            scroll_width * 0.40,
        )

        field_right_padding = 14.0

        field_width = max(
            82.0,
            scroll_width
            - field_x
            - field_right_padding,
        )

        y = 8.0
        current_group = None

        for prop in self._selected_inspector_properties():
            label = self._inspector_labels.get(
                prop.key
            )
            control = self._inspector_controls.get(
                prop.key
            )

            if (
                label is None
                or control is None
                or not label.visible
                or not control.visible
            ):
                continue

            if prop.group != current_group:
                current_group = prop.group

                group = self._inspector_groups.get(
                    current_group
                )

                if (
                    group is not None
                    and group.visible
                ):
                    group.position = (
                        8.0,
                        y,
                    )

                    y += 28.0

            label.position = (
                label_x,
                y + 9.0,
            )

            control.anchor = (
                0.0,
                0.0,
            )
            control.pivot = (
                0.5,
                0.5,
            )

            if prop.kind == "bool":
                # A checkbox is a square control, not a text field. Keeping
                # its own hitbox small prevents it from covering adjacent
                # Inspector inputs.
                checkbox_size = 26.0

                control.size = (
                    checkbox_size,
                    checkbox_size,
                )

                control.position = (
                    field_x + checkbox_size / 2.0,
                    y + 15.0,
                )

            else:
                control.size = (
                    field_width,
                    34.0,
                )

                control.position = (
                    field_x + field_width / 2.0,
                    y + 17.0,
                )

            y += 40.0

        content_height = max(
            scroll_height,
            y + 12.0,
        )

        self.inspector_scroll.set_content_size(
            scroll_width,
            content_height,
        )

    def _sync_bottom_layout(
        self,
        width: float,
        height: float,
    ) -> None:
        self.assets_button.size = (
            82.0,
            32.0,
        )
        self.assets_button.anchor = (
            0.0,
            0.0,
        )
        self.assets_button.pivot = (
            0.5,
            0.5,
        )
        self.assets_button.position = (
            51.0,
            23.0,
        )

        self.console_button.size = (
            92.0,
            32.0,
        )
        self.console_button.anchor = (
            0.0,
            0.0,
        )
        self.console_button.pivot = (
            0.5,
            0.5,
        )
        self.console_button.position = (
            144.0,
            23.0,
        )

        self.animation_button.size = (
            112.0,
            32.0,
        )
        self.animation_button.anchor = (
            0.0,
            0.0,
        )
        self.animation_button.pivot = (
            0.5,
            0.5,
        )
        self.animation_button.position = (
            245.0,
            23.0,
        )

        self.bottom_title.position = (
            490.0,
            13.0,
        )

        # ------------------------------------------------------
        # Assets toolbar
        # ------------------------------------------------------

        toolbar_y = 49.0

        self.asset_up_button.size = (
            54.0,
            28.0,
        )
        self.asset_up_button.anchor = (
            0.0,
            0.0,
        )
        self.asset_up_button.pivot = (
            0.5,
            0.5,
        )
        self.asset_up_button.position = (
            37.0,
            toolbar_y,
        )

        self.asset_refresh_button.size = (
            78.0,
            28.0,
        )
        self.asset_refresh_button.anchor = (
            0.0,
            0.0,
        )
        self.asset_refresh_button.pivot = (
            0.5,
            0.5,
        )
        self.asset_refresh_button.position = (
            108.0,
            toolbar_y,
        )

        search_w = min(
            280.0,
            max(
                160.0,
                width * 0.22,
            ),
        )

        self.asset_search.size = (
            search_w,
            30.0,
        )
        self.asset_search.anchor = (
            0.0,
            0.0,
        )
        self.asset_search.pivot = (
            0.5,
            0.5,
        )
        self.asset_search.position = (
            164.0
            + search_w / 2.0,
            toolbar_y,
        )

        self.asset_path_label.position = (
            175.0
            + search_w,
            39.0,
        )

        content_top = 70.0
        content_bottom_margin = 8.0
        content_h = max(
            0.0,
            height
            - content_top
            - content_bottom_margin,
        )

        preview_w = min(
            150.0,
            max(
                110.0,
                width * 0.12,
            ),
        )

        details_w = min(
            245.0,
            max(
                180.0,
                width * 0.19,
            ),
        )

        right_margin = 8.0
        gap = 8.0

        list_w = max(
            180.0,
            width
            - preview_w
            - details_w
            - right_margin
            - gap * 3.0,
        )

        self.asset_list.size = (
            list_w,
            content_h,
        )
        self.asset_list.anchor = (
            0.0,
            0.0,
        )
        self.asset_list.pivot = (
            0.5,
            0.5,
        )
        self.asset_list.position = (
            8.0
            + list_w / 2.0,
            content_top
            + content_h / 2.0,
        )

        preview_x = (
            8.0
            + list_w
            + gap
        )

        self.asset_preview.size = (
            preview_w,
            content_h,
        )
        self.asset_preview.anchor = (
            0.0,
            0.0,
        )
        self.asset_preview.pivot = (
            0.5,
            0.5,
        )
        self.asset_preview.position = (
            preview_x
            + preview_w / 2.0,
            content_top
            + content_h / 2.0,
        )

        details_x = (
            preview_x
            + preview_w
            + gap
        )

        self.asset_details.position = (
            details_x,
            content_top + 5.0,
        )

        self.console_content.position = (
            18.0,
            76.0,
        )

        self.console_clear_button.size = (
            78.0,
            28.0,
        )
        self.console_clear_button.anchor = (
            1.0,
            0.0,
        )
        self.console_clear_button.pivot = (
            0.5,
            0.5,
        )
        self.console_clear_button.position = (
            width - 48.0,
            toolbar_y,
        )

        # ------------------------------------------------------
        # Animation editor
        # ------------------------------------------------------

        animation_list_width = min(
            230.0,
            max(170.0, width * 0.18),
        )
        animation_top = 70.0
        animation_height = max(
            0.0,
            height - animation_top - content_bottom_margin,
        )
        animation_frame_width = max(
            240.0,
            width - animation_list_width - 28.0,
        )

        self.animation_list.size = (
            animation_list_width,
            animation_height,
        )
        self.animation_list.anchor = (0.0, 0.0)
        self.animation_list.pivot = (0.5, 0.5)
        self.animation_list.position = (
            8.0 + animation_list_width / 2.0,
            animation_top + animation_height / 2.0,
        )

        self.animation_frame_list.size = (
            animation_frame_width,
            animation_height,
        )
        self.animation_frame_list.anchor = (0.0, 0.0)
        self.animation_frame_list.pivot = (0.5, 0.5)
        self.animation_frame_list.position = (
            16.0 + animation_list_width + animation_frame_width / 2.0,
            animation_top + animation_height / 2.0,
        )

        self.animation_status_label.position = (
            16.0 + animation_list_width,
            52.0,
        )
        animation_button_y = 49.0
        self.animation_new_button.size = (58.0, 28.0)
        self.animation_new_button.anchor = (0.0, 0.0)
        self.animation_new_button.pivot = (0.5, 0.5)
        self.animation_new_button.position = (37.0, animation_button_y)
        animation_button_x = width - 246.0
        for button, button_width in (
            (self.animation_play_button, 64.0),
            (self.animation_pause_button, 70.0),
            (self.animation_stop_button, 64.0),
        ):
            button.size = (button_width, 28.0)
            button.anchor = (0.0, 0.0)
            button.pivot = (0.5, 0.5)
            button.position = (
                animation_button_x + button_width / 2.0,
                animation_button_y,
            )
            animation_button_x += button_width + 5.0

        self.animation_speed_input.size = (70.0, 28.0)
        self.animation_speed_input.anchor = (1.0, 0.0)
        self.animation_speed_input.pivot = (0.5, 0.5)
        self.animation_speed_input.position = (
            width - 42.0,
            animation_button_y,
        )

        # Fixed context menu at the right edge of the asset list. It appears
        # only after right-clicking an item and therefore does not permanently
        # consume dock space.
        context_w = 96.0
        context_h = 102.0

        self.asset_context.size = (
            context_w,
            context_h,
        )
        self.asset_context.anchor = (
            0.0,
            0.0,
        )
        self.asset_context.pivot = (
            0.5,
            0.5,
        )
        self.asset_context.position = (
            max(
                context_w / 2.0 + 8.0,
                list_w
                - context_w / 2.0,
            ),
            content_top
            + context_h / 2.0
            + 4.0,
        )

        context_buttons = (
            self.asset_context_open,
            self.asset_context_reveal,
            self.asset_context_refresh,
        )

        for index, button in enumerate(
            context_buttons
        ):
            button.size = (
                82.0,
                26.0,
            )
            button.anchor = (
                0.5,
                0.0,
            )
            button.pivot = (
                0.5,
                0.5,
            )
            button.position = (
                0.0,
                18.0
                + index * 31.0,
            )

    def _sync_status_layout(self, width: float) -> None:
        self.status_label.position = (12.0, 0.0)
        self.engine_label.position = (-12.0, 0.0)
