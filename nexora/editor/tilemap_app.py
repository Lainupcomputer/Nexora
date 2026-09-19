from __future__ import annotations

from pathlib import Path

from nexora import Game
from nexora.editor.commands import (
    CommandStack,
    TileMapLayerAddCommand,
    TileMapLayerPropertyCommand,
    TileMapLayerRemoveCommand,
    TileMapLayerRenameCommand,
    TileMapPaintCommand,
    TileMapProjectionCommand,
)
from nexora.editor.model import EditorDocument, SelectionService
from nexora.editor.tilemap import TileMapEditorModel
from nexora.editor.tile_palette import TilePalette
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
from nexora.editor.viewport import EditorViewportCanvas, EditorViewportState
from nexora.nodes import (
    Button,
    CheckBox,
    ConfirmDialog,
    Dialog,
    Dropdown,
    FileDialog,
    Label,
    ListView,
    Panel,
    TextInput,
)
from nexora.nodes.world.tilemap_node import TileMapNode
from nexora.scene import Scene
from nexora.tilemap import TILEMAP_ASSET_SUFFIX, TileMap, TileMapAsset, TileProjection, TileSet
from nexora.tilemap.tile_layer import LAYER_ROLES, normalize_layer_role

from nexora.editor.app import resolve_project_path


class TileMapEditorScene(Scene):
    """Standalone editor for authoring portable ``.tilemap.net`` assets."""

    TOOLBAR_HEIGHT = 48.0
    STATUS_HEIGHT = 26.0
    LEFT_WIDTH = 220.0
    # The inspector contains two-column settings and therefore needs the
    # same minimum width as the regular editor inspector.  Keeping this
    # width fixed also prevents controls from crossing into the viewport at
    # the default 1440px window size.
    RIGHT_WIDTH = 310.0
    BOTTOM_HEIGHT = 210.0
    GAP = 1.0
    LAYER_ROLE_LABELS = tuple(role.title() for role in LAYER_ROLES)

    def __init__(
        self,
        game,
        project_path: Path,
        *,
        document: EditorDocument,
        selection: SelectionService,
    ) -> None:
        super().__init__("NexoraTileMapEditor")
        self.game = game
        self.project_path = Path(project_path).resolve()
        self.document = document
        self.selection = selection
        self.commands = CommandStack()
        self.viewport_state = EditorViewportState()
        self.tilemap_tool = "paint"
        self._tilemap_model = None
        self._tilemap_drag_cells = None
        self._tilemap_hover_cell = None
        self._last_size = (-1.0, -1.0)
        self._pending_action = None
        self._pending_tileset_path: Path | None = None
        self._tileset_setup_image_size: tuple[int, int] | None = None
        self._build_ui()

    # ----------------------------------------------------------
    # UI construction
    # ----------------------------------------------------------

    def _build_ui(self) -> None:
        root = self.ui
        self.background = root.create_child("EditorBackground", node_type=Panel)
        self.background.background = EDITOR_BACKGROUND
        self.toolbar = root.create_child("Toolbar", node_type=Panel)
        self.toolbar.background = TOOLBAR_BACKGROUND
        self.toolbar.border_color = PANEL_BORDER
        self.toolbar.border_width = 1.0
        self.map_panel = root.create_child("MapPanel", node_type=Panel)
        self._style_panel(self.map_panel)
        self.viewport = root.create_child("Viewport", node_type=Panel)
        self.viewport.background = VIEWPORT_BACKGROUND
        self.viewport.border_color = PANEL_BORDER
        self.viewport.border_width = 1.0
        self.info_panel = root.create_child("InfoPanel", node_type=Panel)
        self._style_panel(self.info_panel)
        self.bottom_dock = root.create_child("BottomDock", node_type=Panel)
        self.bottom_dock.background = PANEL_BACKGROUND_DARK
        self.bottom_dock.border_color = PANEL_BORDER
        self.bottom_dock.border_width = 1.0
        self.status_bar = root.create_child("StatusBar", node_type=Panel)
        self.status_bar.background = TOOLBAR_BACKGROUND
        self.status_bar.border_color = PANEL_BORDER
        self.status_bar.border_width = 1.0

        self._build_toolbar()
        self._build_map_panel()
        self._build_viewport()
        self._build_info_panel()
        self._build_bottom_dock()
        self._build_dialogs()
        self._build_status_bar()
        self.selection.changed.connect(self._on_selection_changed)
        self._refresh_document_ui()

    def _style_panel(self, panel: Panel) -> None:
        panel.background = PANEL_BACKGROUND
        panel.border_color = PANEL_BORDER
        panel.border_width = 1.0

    def _button(self, parent: Panel, name: str, text: str, callback) -> Button:
        button = parent.create_child(name, node_type=Button)
        button.text = text
        button.text_scale = 0.68
        button.normal_background = BUTTON_BACKGROUND
        button.hover_background = BUTTON_HOVER
        button.pressed_background = BUTTON_PRESSED
        button.focus_background = BUTTON_HOVER
        button.focus_border_color = ACCENT
        button.on_click = callback
        return button

    def _label(self, parent: Panel, name: str, text: str, scale: float = 0.62) -> Label:
        label = parent.create_child(name, node_type=Label)
        label.text = text
        label.scale = scale
        label.anchor = (0.0, 0.0)
        label.pivot = (0.0, 0.0)
        return label

    def _build_toolbar(self) -> None:
        self.brand_label = self._label(self.toolbar, "Brand", "NEXORA", 0.9)
        self.new_button = self._button(self.toolbar, "NewButton", "New", self.request_new_map)
        self.open_button = self._button(self.toolbar, "OpenButton", "Open", self.request_open_map)
        self.save_button = self._button(self.toolbar, "SaveButton", "Save", self.save_map)
        self.save_as_button = self._button(self.toolbar, "SaveAsButton", "Save As", self.save_map_as)
        self.tileset_button = self._button(self.toolbar, "TilesetButton", "Tileset", self.open_tileset_browser)
        self.scene_editor_button = self._button(
            self.toolbar, "SceneEditorButton", "Scene Editor", self._open_scene_editor
        )
        self.undo_button = self._button(self.toolbar, "UndoButton", "Undo", self.undo)
        self.redo_button = self._button(self.toolbar, "RedoButton", "Redo", self.redo)
        self.document_label = self._label(self.toolbar, "DocumentLabel", "", 0.68)
        self.document_label.anchor = (1.0, 0.5)
        self.document_label.pivot = (1.0, 0.5)

    def _build_map_panel(self) -> None:
        self.map_title = self._label(self.map_panel, "MapTitle", "Map Layers", 0.78)
        self.layer_list = self.map_panel.create_child("Layers", node_type=ListView)
        self.layer_list.item_height = 30.0
        self.layer_list.spacing = 1.0
        self.layer_list.padding_left = 5.0
        self.layer_list.padding_right = 5.0
        self.layer_list.padding_top = 5.0
        self.layer_list.padding_bottom = 5.0
        self.layer_list.text_padding_left = 7.0
        self.layer_list.text_scale = 0.62
        self.layer_list.on_change = self._on_layer_selected
        self.layer_hint = self._label(
            self.map_panel,
            "LayerHint",
            "Paint on active layer.",
            0.52,
        )
        self.add_layer_button = self._button(self.map_panel, "AddLayerButton", "+ Layer", self.add_layer)
        self.remove_layer_button = self._button(self.map_panel, "RemoveLayerButton", "- Layer", self.remove_layer)

    def _build_viewport(self) -> None:
        self.viewport_canvas = self.viewport.create_child(
            "ViewportCanvas", node_type=EditorViewportCanvas
        )
        self.viewport_canvas.editor_scene = self
        self.viewport_title = self._label(self.viewport, "ViewportTitle", "2D TileMap View", 0.78)
        self.viewport_subtitle = self._label(self.viewport, "ViewportSubtitle", "", 0.58)
        self.viewport_controls = self._label(
            self.viewport,
            "ViewportControls",
            "P Paint   X Erase   B Fill   MMB Pan   Wheel Zoom",
            0.54,
        )
        self.tool_label = self._label(self.viewport, "ToolLabel", "", 0.56)
        self.select_button = self._button(self.viewport, "SelectButton", "Select", lambda: self._set_tilemap_tool("select"))
        self.paint_button = self._button(self.viewport, "PaintButton", "Paint", lambda: self._set_tilemap_tool("paint"))
        self.erase_button = self._button(self.viewport, "EraseButton", "Erase", lambda: self._set_tilemap_tool("erase"))
        self.fill_button = self._button(self.viewport, "FillButton", "Fill", lambda: self._set_tilemap_tool("fill"))
        self.projection_button = self._button(
            self.viewport, "ProjectionButton", "Angled 2D", self._set_angled_2d_projection
        )
        self.tile_input = self.viewport.create_child("TileInput", node_type=TextInput)
        self.tile_input.placeholder = "Tile ID"
        self.tile_input.set_text("0", emit=False)
        self.tile_input.auto_size = False

    def _build_info_panel(self) -> None:
        self.info_title = self._label(self.info_panel, "InfoTitle", "TileMap", 0.78)
        self.info_label = self._label(self.info_panel, "Info", "", 0.58)
        self.layer_inspector_title = self._label(self.info_panel, "LayerInspectorTitle", "Selected Layer", 0.64)
        self.layer_name_label = self._label(self.info_panel, "LayerNameLabel", "Name", 0.48)
        self.layer_name_input = self.info_panel.create_child("LayerName", node_type=TextInput)
        self.layer_name_input.auto_size = False
        self.layer_name_input.text_scale = 0.62
        self.layer_name_input.on_submit = self._on_layer_name_submitted
        self.layer_role_label = self._label(self.info_panel, "LayerRoleLabel", "Role", 0.48)
        self.layer_role_dropdown = self.info_panel.create_child("LayerRole", node_type=Dropdown)
        self.layer_role_dropdown.set_options(self.LAYER_ROLE_LABELS)
        self.layer_role_dropdown.on_change = self._on_layer_role_changed
        self.layer_visible_checkbox = self.info_panel.create_child("LayerVisible", node_type=CheckBox)
        self.layer_visible_checkbox.text = "Visible"
        self.layer_visible_checkbox.text_scale = 0.58
        self.layer_visible_checkbox.on_change = lambda value: self._set_layer_property("visible", value)
        self.layer_enabled_checkbox = self.info_panel.create_child("LayerEnabled", node_type=CheckBox)
        self.layer_enabled_checkbox.text = "Enabled"
        self.layer_enabled_checkbox.text_scale = 0.58
        self.layer_enabled_checkbox.on_change = lambda value: self._set_layer_property("enabled", value)
        self.layer_render_label = self._label(self.info_panel, "LayerRenderLabel", "Render Layer", 0.48)
        self.layer_render_input = self.info_panel.create_child("LayerRender", node_type=TextInput)
        self.layer_render_input.auto_size = False
        self.layer_render_input.text_scale = 0.62
        self.layer_render_input.on_submit = self._on_layer_render_submitted
        self.layer_opacity_label = self._label(self.info_panel, "LayerOpacityLabel", "Opacity", 0.48)
        self.layer_opacity_input = self.info_panel.create_child("LayerOpacity", node_type=TextInput)
        self.layer_opacity_input.auto_size = False
        self.layer_opacity_input.text_scale = 0.62
        self.layer_opacity_input.on_submit = self._on_layer_opacity_submitted
        self.layer_y_sort_checkbox = self.info_panel.create_child("LayerYSort", node_type=CheckBox)
        self.layer_y_sort_checkbox.text = "Y-Sort"
        self.layer_y_sort_checkbox.text_scale = 0.58
        self.layer_y_sort_checkbox.on_change = lambda value: self._set_layer_property("y_sort", value)
        self.layer_role_hint = self._label(
            self.info_panel,
            "LayerRoleHint",
            "Roles: Ground, Objects, Collision, Trigger ...",
            0.43,
        )
        self.config_title = self._label(self.info_panel, "ConfigTitle", "Tileset / Map Settings", 0.64)
        self.tileset_path_label = self._label(self.info_panel, "TilesetPath", "No tileset selected", 0.48)
        self.apply_tileset_button = self._button(self.info_panel, "ApplyTileset", "Apply Tileset", self.apply_tileset_settings)
        self.apply_map_button = self._button(self.info_panel, "ApplyMap", "Apply Map Size", self.apply_map_settings)
        self._config_labels = {}
        self.map_width_input = self._config_input("MapWidth", "Map W", "16")
        self.map_height_input = self._config_input("MapHeight", "Map H", "16")
        self.tile_width_input = self._config_input("TileWidth", "Tile W", "32")
        self.tile_height_input = self._config_input("TileHeight", "Tile H", "32")
        self.gap_x_input = self._config_input("GapX", "Gap X", "0")
        self.gap_y_input = self._config_input("GapY", "Gap Y", "0")
        self.margin_x_input = self._config_input("MarginX", "Margin X", "0")
        self.margin_y_input = self._config_input("MarginY", "Margin Y", "0")

    def _config_input(self, name: str, label: str, value: str) -> TextInput:
        self._config_labels[name] = self._label(self.info_panel, f"{name}Label", label, 0.48)
        input_node = self.info_panel.create_child(name, node_type=TextInput)
        input_node.set_text(value, emit=False)
        input_node.auto_size = False
        input_node.text_scale = 0.62
        return input_node

    def _build_bottom_dock(self) -> None:
        self.palette_title = self._label(self.bottom_dock, "PaletteTitle", "Tile Palette", 0.78)
        self.tile_palette = self.bottom_dock.create_child("TilePalette", node_type=TilePalette)
        self.tile_palette.on_change = self._on_tile_selected
        self.palette_hint = self._label(
            self.bottom_dock,
            "PaletteHint",
            "No tileset selected - click Tileset to choose an image.",
            0.55,
        )

    def _build_dialogs(self) -> None:
        self.new_map_dialog = self.ui.create_child("NewMapDialog", node_type=Dialog)
        self.new_map_dialog.title = "New TileMap"
        self.new_map_dialog.confirm_text = "Create"
        self.new_map_dialog.dialog_size = (520.0, 235.0)
        self.new_map_name = self.new_map_dialog.content.create_child("MapName", node_type=TextInput)
        self.new_map_name.placeholder = "Map name"
        self.new_map_name.size = (450.0, 44.0)
        self.new_map_name.anchor = (0.5, 0.5)
        self.new_map_name.pivot = (0.5, 0.5)
        self.new_map_name.on_submit = lambda _text: self.new_map_dialog.confirm()
        self.new_map_dialog.on_confirm = self._create_new_map

        self.open_dialog = self.ui.create_child("OpenMapDialog", node_type=FileDialog)
        self.open_dialog.file_selected.connect(self._on_open_map_selected)
        self.save_dialog = self.ui.create_child("SaveMapDialog", node_type=FileDialog)
        self.save_dialog.file_selected.connect(self._on_save_map_selected)
        self.tileset_dialog = self.ui.create_child("TilesetDialog", node_type=FileDialog)
        self.tileset_dialog.file_selected.connect(self._on_tileset_selected)

        self.tileset_setup_dialog = self.ui.create_child("TilesetSetupDialog", node_type=Dialog)
        self.tileset_setup_dialog.dialog_size = (680.0, 430.0)
        self.tileset_setup_dialog.title = "Tileset Setup"
        self.tileset_setup_dialog.confirm_text = "Apply Tileset"
        self.tileset_setup_dialog.cancel_text = "Cancel"
        self.tileset_setup_dialog.close_on_confirm = False
        self.tileset_setup_dialog.on_confirm = self._confirm_tileset_setup
        self.tileset_setup_info = self.tileset_setup_dialog.content.create_child(
            "TilesetSetupInfo", node_type=Label
        )
        self.tileset_setup_info.scale = 0.62
        self.tileset_setup_error = self.tileset_setup_dialog.content.create_child(
            "TilesetSetupError", node_type=Label
        )
        self.tileset_setup_error.scale = 0.52
        self.tileset_setup_error.text = ""
        self.tileset_setup_summary = self.tileset_setup_dialog.content.create_child(
            "TilesetSetupSummary", node_type=Label
        )
        self.tileset_setup_summary.scale = 0.52
        self.tileset_setup_inputs: dict[str, TextInput] = {}
        for name, label, fallback in (
            ("tile_width", "Tile Width", "32"),
            ("tile_height", "Tile Height", "32"),
            ("gap_x", "Gap X", "0"),
            ("gap_y", "Gap Y", "0"),
            ("margin_x", "Margin X", "0"),
            ("margin_y", "Margin Y", "0"),
        ):
            label_node = self.tileset_setup_dialog.content.create_child(
                f"TilesetSetup{label.replace(' ', '')}Label", node_type=Label
            )
            label_node.text = label
            label_node.scale = 0.48
            input_node = self.tileset_setup_dialog.content.create_child(
                f"TilesetSetup{label.replace(' ', '')}", node_type=TextInput
            )
            input_node.auto_size = False
            input_node.text_scale = 0.62
            input_node.set_text(fallback, emit=False)
            input_node.on_change = lambda _value: self._update_tileset_setup_summary()
            self.tileset_setup_inputs[name] = input_node
            setattr(self, f"tileset_setup_{name}_label", label_node)

        self._sync_tileset_setup_layout()

        self.unsaved_dialog = self.ui.create_child("UnsavedDialog", node_type=ConfirmDialog)
        self.unsaved_dialog.title = "Unsaved Changes"
        self.unsaved_dialog.confirm_text = "Discard"
        self.unsaved_dialog.cancel_text = "Cancel"
        self.unsaved_dialog.message = "The current map has unsaved changes.\nDiscard them and continue?"
        self.unsaved_dialog.on_confirm = self._continue_pending_action
        self.unsaved_dialog.on_cancel = self._clear_pending_action

        self.error_dialog = self.ui.create_child("ErrorDialog", node_type=ConfirmDialog)
        self.error_dialog.title = "TileMap Editor Error"
        self.error_dialog.confirm_text = "OK"
        self.error_dialog.show_cancel_button = False

    def _build_status_bar(self) -> None:
        self.status_label = self._label(self.status_bar, "Status", "Ready", 0.60)
        self.status_label.anchor = (0.0, 0.5)
        self.status_label.pivot = (0.0, 0.5)
        self.version_label = self._label(self.status_bar, "Version", "Nexora TileMap Editor v0.10", 0.60)
        self.version_label.anchor = (1.0, 0.5)
        self.version_label.pivot = (1.0, 0.5)

    # ----------------------------------------------------------
    # Document workflow
    # ----------------------------------------------------------

    def _serialization_context(self) -> dict:
        context = {
            "game": self.game,
            "engine": self.game.engine,
            "renderer": self.game.renderer,
            "input": self.game.input,
            "scene": self.document.scene,
        }
        if self.game.engine is not None:
            context["assets"] = self.game.engine.assets
            context["audio"] = self.game.engine.audio
        return context

    def _asset_root(self) -> Path:
        assets = self.project_path / "assets"
        return assets if assets.is_dir() else self.project_path

    def _asset_start_directory(self) -> Path:
        root = self._asset_root()
        tilemaps = root / "tilemaps"
        return tilemaps if tilemaps.is_dir() else root

    def _run_after_dirty_check(self, action) -> None:
        if self.document.dirty:
            self._pending_action = action
            self.unsaved_dialog.open()
        else:
            action()

    def _continue_pending_action(self) -> None:
        action = self._pending_action
        self._pending_action = None
        if action is not None:
            action()

    def _clear_pending_action(self) -> None:
        self._pending_action = None

    def request_new_map(self) -> None:
        self._run_after_dirty_check(self._open_new_map_dialog)

    def _open_new_map_dialog(self) -> None:
        self.new_map_name.set_text("Untitled", emit=False)
        self.new_map_dialog.open(focus=self.new_map_name)

    def _create_new_map(self) -> None:
        name = self.new_map_name.text.strip() or "Untitled"
        scene = self.document.new(name)
        node = self._create_blank_tilemap(scene)
        self.document.path = None
        self._pending_tileset_path = None
        self.commands.clear()
        self._set_tilemap_node(node)
        self.status_label.text = f"Created TileMap {name}"

    def _create_blank_tilemap(self, scene: Scene) -> TileMapNode:
        node = TileMapNode("TileMap", scene.world)
        width, height = self._read_config_pair(self.map_width_input, self.map_height_input, (16, 16))
        tile_width, tile_height = self._read_config_pair(self.tile_width_input, self.tile_height_input, (32, 32))
        tilemap = TileMap(
            width=width,
            height=height,
            tile_width=tile_width,
            tile_height=tile_height,
            name=scene.name,
            projection=TileProjection.ANGLED_2D,
        )
        tilemap.create_layer("ground")
        tileset = TileSet(
            columns=1,
            rows=1,
            tile_width=tile_width,
            tile_height=tile_height,
            name="DefaultTileSet",
            spacing_x=self._read_int(self.gap_x_input, 0),
            spacing_y=self._read_int(self.gap_y_input, 0),
            margin_x=self._read_int(self.margin_x_input, 0),
            margin_y=self._read_int(self.margin_y_input, 0),
        )
        node.set_map(tilemap, tileset, None)
        scene.root.add_child(node)
        return node

    def request_open_map(self) -> None:
        self._run_after_dirty_check(self._open_map_file_dialog)

    def _open_map_file_dialog(self) -> None:
        self.open_dialog.configure(
            mode="open",
            root_path=self._asset_root(),
            current_path=self._asset_start_directory(),
            extensions=(TILEMAP_ASSET_SUFFIX,),
            title="Open TileMap Asset",
        )
        self.open_dialog.open()

    def open_path(self, path: str | Path) -> None:
        resolved = Path(path).expanduser()
        if not resolved.is_absolute():
            candidate = self.project_path / resolved
            resolved = candidate if candidate.exists() else self._asset_root() / resolved
        self._load_map(resolved.resolve())

    def _on_open_map_selected(self, _dialog, path: Path) -> None:
        self._load_map(path)

    def _load_map(self, path: Path) -> None:
        try:
            asset = TileMapAsset.load(path)
            tilemap, tileset = asset.build()
            scene = self.document.new(asset.name)
            node = TileMapNode("TileMap", scene.world)
            texture = None
            if tileset.texture_asset and self.game.engine is not None:
                texture = self.game.engine.assets.texture(tileset.texture_asset)
            node.set_map(tilemap, tileset, texture)
            node.tilemap_asset = self._asset_relative(path)
            self._pending_tileset_path = (
                self._asset_root() / tileset.texture_asset
                if tileset.texture_asset
                else None
            )
            scene.root.add_child(node)
            self.document.path = path.resolve()
            self.document.mark_clean()
        except Exception as exc:
            self._show_error(f"Could not open TileMap asset:\n{exc}")
            return
        self.commands.clear()
        self._set_tilemap_node(node)
        self.status_label.text = f"Opened {path.name}"

    def save_map(self) -> None:
        if self.document.path is None:
            self.save_map_as()
            return
        try:
            path = self._save_asset(self.document.path)
        except Exception as exc:
            self._show_error(f"Could not save TileMap asset:\n{exc}")
            return
        self._refresh_document_ui()
        self.status_label.text = f"Saved {path.name}"

    def save_map_as(self) -> None:
        self.save_dialog.configure(
            mode="save",
            root_path=self._asset_root(),
            current_path=self._asset_start_directory(),
            extensions=(TILEMAP_ASSET_SUFFIX,),
            title="Save TileMap Asset As",
        )
        base_name = self.document.display_name
        if self.document.path is not None and self.document.path.name.lower().endswith(TILEMAP_ASSET_SUFFIX):
            base_name = self.document.path.name[: -len(TILEMAP_ASSET_SUFFIX)]
        self.save_dialog.filename_input.set_text(f"{base_name}{TILEMAP_ASSET_SUFFIX}", emit=False)
        self.save_dialog.open(focus=self.save_dialog.filename_input)

    def _on_save_map_selected(self, _dialog, path: Path) -> None:
        try:
            saved = self._save_asset(path)
        except Exception as exc:
            self._show_error(f"Could not save TileMap asset:\n{exc}")
            return
        self._refresh_document_ui()
        self.status_label.text = f"Saved {saved.name}"

    def _read_int(self, input_node: TextInput, default: int) -> int:
        try:
            return max(0, int(input_node.text.strip()))
        except (TypeError, ValueError):
            return int(default)

    def _read_config_pair(self, first: TextInput, second: TextInput, default: tuple[int, int]) -> tuple[int, int]:
        return max(1, self._read_int(first, default[0])), max(1, self._read_int(second, default[1]))

    def _asset_relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self._asset_root().resolve()).as_posix()
        except ValueError:
            return path.name

    def _save_asset(self, path: Path) -> Path:
        model = self._selected_tilemap_editor_model()
        if model is None or model.node.tilemap is None or model.node.tileset is None:
            raise RuntimeError("No TileMap is ready to save.")
        if not model.tileset.texture_asset:
            raise RuntimeError("Select a tileset image before saving the TileMap asset.")
        saved = TileMapAsset.from_components(model.tilemap, model.tileset, name=model.tilemap.name).save(path)
        self.document.path = saved
        self.document.mark_clean()
        model.node.tilemap_asset = self._asset_relative(saved)
        return saved

    def open_tileset_browser(self) -> None:
        self.tileset_dialog.configure(
            mode="open",
            root_path=self._asset_root(),
            current_path=self._asset_root(),
            extensions=(".png", ".jpg", ".jpeg", ".bmp", ".webp"),
            title="Choose Tileset Image",
            activate_on_single_click=True,
        )
        self.tileset_dialog.open()

    def _on_tileset_selected(self, _dialog, path: Path) -> None:
        self._pending_tileset_path = path.resolve()
        self.tileset_path_label.text = self._asset_relative(path)
        try:
            image = self.game.engine.assets.image(self._pending_tileset_path)
        except Exception as exc:
            self._show_error(f"Could not read tileset image:\n{exc}")
            return

        self._tileset_setup_image_size = (int(image.width), int(image.height))
        self.tileset_setup_info.text = (
            f"Image: {image.width} x {image.height} px\n"
            f"Asset: {self._asset_relative(path)}"
        )
        self.tileset_setup_error.text = (
            "Set the grid values, then apply the tileset."
        )
        for name, source in (
            ("tile_width", self.tile_width_input),
            ("tile_height", self.tile_height_input),
            ("gap_x", self.gap_x_input),
            ("gap_y", self.gap_y_input),
            ("margin_x", self.margin_x_input),
            ("margin_y", self.margin_y_input),
        ):
            self.tileset_setup_inputs[name].set_text(source.text, emit=False)
        self._update_tileset_setup_summary()
        self.tileset_setup_dialog.open(focus=self.tileset_setup_inputs["tile_width"])
        self.status_label.text = "Tileset selected. Configure the tile grid."

    def _setup_int(self, name: str, default: int = 0) -> int:
        input_node = self.tileset_setup_inputs[name]
        try:
            return int(input_node.text.strip())
        except (TypeError, ValueError):
            return int(default)

    def _update_tileset_setup_summary(self) -> None:
        if self._tileset_setup_image_size is None:
            self.tileset_setup_summary.text = ""
            return
        image_width, image_height = self._tileset_setup_image_size
        tile_width = self._setup_int("tile_width", 32)
        tile_height = self._setup_int("tile_height", 32)
        gap_x = self._setup_int("gap_x", 0)
        gap_y = self._setup_int("gap_y", 0)
        margin_x = self._setup_int("margin_x", 0)
        margin_y = self._setup_int("margin_y", 0)
        if tile_width <= 0 or tile_height <= 0 or gap_x < 0 or gap_y < 0:
            self.tileset_setup_summary.text = "Grid values are not valid yet."
            return
        usable_width = image_width - margin_x * 2
        usable_height = image_height - margin_y * 2
        columns = (usable_width + gap_x) // (tile_width + gap_x) if usable_width > 0 else 0
        rows = (usable_height + gap_y) // (tile_height + gap_y) if usable_height > 0 else 0
        fits = (
            columns > 0
            and rows > 0
            and columns * tile_width + max(0, columns - 1) * gap_x == usable_width
            and rows * tile_height + max(0, rows - 1) * gap_y == usable_height
        )
        self.tileset_setup_summary.text = (
            f"Detected grid: {columns} x {rows} tiles"
            if fits
            else "Grid does not fit the image exactly yet."
        )

    def _confirm_tileset_setup(self) -> None:
        for name, target in (
            ("tile_width", self.tile_width_input),
            ("tile_height", self.tile_height_input),
            ("gap_x", self.gap_x_input),
            ("gap_y", self.gap_y_input),
            ("margin_x", self.margin_x_input),
            ("margin_y", self.margin_y_input),
        ):
            target.set_text(self.tileset_setup_inputs[name].text, emit=False)
        if self.apply_tileset_settings(show_error=False):
            self.tileset_setup_dialog.close()


    def apply_tileset_settings(self, *, show_error: bool = True) -> bool:
        model = self._selected_tilemap_editor_model()
        if model is None:
            self.status_label.text = "Create or open a TileMap asset first."
            return False
        if self._pending_tileset_path is None:
            self.status_label.text = "Choose a tileset image first."
            return False
        try:
            texture_asset = self._asset_relative(self._pending_tileset_path)
            image = self.game.engine.assets.image(self._pending_tileset_path)
            tile_width, tile_height = self._read_config_pair(self.tile_width_input, self.tile_height_input, (32, 32))
            gap_x = self._read_int(self.gap_x_input, 0)
            gap_y = self._read_int(self.gap_y_input, 0)
            margin_x = self._read_int(self.margin_x_input, 0)
            margin_y = self._read_int(self.margin_y_input, 0)
            usable_width = int(image.width) - margin_x * 2
            usable_height = int(image.height) - margin_y * 2
            columns = (usable_width + gap_x) // (tile_width + gap_x)
            rows = (usable_height + gap_y) // (tile_height + gap_y)
            if columns <= 0 or rows <= 0:
                raise ValueError("Tile size and margins do not fit the selected image.")
            expected_width = columns * tile_width + max(0, columns - 1) * gap_x
            expected_height = rows * tile_height + max(0, rows - 1) * gap_y
            if expected_width != usable_width or expected_height != usable_height:
                raise ValueError("Grid does not fit image; adjust tile size, gap, or margin.")
            tileset = TileSet(
                name=self._pending_tileset_path.stem,
                columns=columns,
                rows=rows,
                tile_width=tile_width,
                tile_height=tile_height,
                texture_asset=texture_asset,
                spacing_x=gap_x,
                spacing_y=gap_y,
                margin_x=margin_x,
                margin_y=margin_y,
            )
            model.tilemap.tile_width = tile_width
            model.tilemap.tile_height = tile_height
            texture = self.game.engine.assets.texture(self._pending_tileset_path)
            model.node.set_map(model.tilemap, tileset, texture)
            model.node.tilemap_asset = None
            self.document.mark_dirty()
            self._refresh_document_ui()
            self.status_label.text = f"Tileset applied: {columns} x {rows} tiles"
            self.tileset_setup_error.text = "Tileset is ready."
            return True
        except Exception as exc:
            message = str(exc)
            if self.tileset_setup_dialog.is_open:
                self.tileset_setup_error.text = message
                self._update_tileset_setup_summary()
            elif show_error:
                self._show_error(f"Could not apply tileset:\n{message}")
            else:
                self.status_label.text = message
            return False

    def apply_map_settings(self) -> None:
        model = self._selected_tilemap_editor_model()
        if model is None:
            return
        width, height = self._read_config_pair(self.map_width_input, self.map_height_input, model.tilemap.size)
        if (width, height) == model.tilemap.size:
            self.status_label.text = "Map size is unchanged"
            return
        old_map = model.tilemap
        new_map = TileMap(
            name=old_map.name,
            width=width,
            height=height,
            tile_width=old_map.tile_width,
            tile_height=old_map.tile_height,
            projection=old_map.projection,
        )
        for old_layer in old_map.layers:
            new_layer = new_map.create_layer(
                old_layer.name,
                visible=old_layer.visible,
                enabled=old_layer.enabled,
                opacity=old_layer.opacity,
                render_layer=old_layer.render_layer,
                y_sort=old_layer.y_sort,
                role=old_layer.role,
            )
            for y in range(min(height, old_layer.height)):
                for x in range(min(width, old_layer.width)):
                    tile_id = old_layer.get_tile(x, y)
                    if tile_id >= 0:
                        new_layer.set_tile(x, y, tile_id)
        node = model.node
        node.set_map(new_map, model.tileset, node.texture)
        self._tilemap_model = None
        self.document.mark_dirty()
        self._refresh_document_ui()
        self.status_label.text = f"Map resized to {width} x {height}"

    def add_layer(self) -> None:
        model = self._selected_tilemap_editor_model()
        if model is None:
            return
        index = 1
        while model.tilemap.has_layer(f"Layer {index}"):
            index += 1
        name = f"Layer {index}"
        self.commands.execute(TileMapLayerAddCommand(model.tilemap, name))
        model.set_active_layer(name)
        self.document.mark_dirty()
        self._refresh_document_ui()
        self.status_label.text = f"Added layer: {name}"

    def remove_layer(self) -> None:
        model = self._selected_tilemap_editor_model()
        if model is None or model.tilemap.layer_count <= 1:
            self.status_label.text = "A TileMap needs at least one layer."
            return
        name = model.active_layer_name
        self.commands.execute(TileMapLayerRemoveCommand(model.tilemap, name))
        model.set_active_layer(model.tilemap.layer_names[0])
        self.document.mark_dirty()
        self._refresh_document_ui()
        self.status_label.text = f"Removed layer: {name}"

    def _show_error(self, message: str) -> None:
        self.error_dialog.message = str(message)
        self.error_dialog.open()

    def _open_scene_editor(self) -> None:
        import subprocess
        import sys

        command = [sys.executable, "-m", "nexora", "--editor", str(self.project_path)]
        try:
            subprocess.Popen(command, cwd=str(self.project_path))
            self.status_label.text = "Scene Editor gestartet"
        except OSError as exc:
            self._show_error(f"Could not start Scene Editor:\n{exc}")

    # ----------------------------------------------------------
    # TileMap operations
    # ----------------------------------------------------------

    @staticmethod
    def _find_tilemap_node(root) -> TileMapNode | None:
        if isinstance(root, TileMapNode):
            return root
        for child in tuple(getattr(root, "children", ())):
            found = TileMapEditorScene._find_tilemap_node(child)
            if found is not None:
                return found
        return None

    def _set_tilemap_node(self, node: TileMapNode | None) -> None:
        self._tilemap_drag_cells = None
        self._tilemap_hover_cell = None
        self._tilemap_model = None
        if node is not None:
            self._tilemap_model = TileMapEditorModel(node)
            self.selection.select(node)
        else:
            self.selection.clear()
        self._refresh_document_ui()

    def _selected_tilemap_editor_model(self):
        node = self.selection.selected
        if not isinstance(node, TileMapNode) or node.tilemap is None or node.tileset is None:
            return None
        if self._tilemap_model is None or self._tilemap_model.node is not node:
            self._tilemap_model = TileMapEditorModel(node)
        if self._tilemap_model.active_layer_name not in node.tilemap.layer_names and node.tilemap.layer_count:
            self._tilemap_model.set_active_layer(node.tilemap.layer_names[0])
        return self._tilemap_model

    def _selected_layer(self):
        model = self._selected_tilemap_editor_model()
        if model is None or model.active_layer_name is None:
            return None
        return model.active_layer

    def _set_layer_property(self, property_name: str, value) -> None:
        layer = self._selected_layer()
        if layer is None or getattr(layer, property_name) == value:
            return
        try:
            self.commands.execute(TileMapLayerPropertyCommand(layer, property_name, value))
            self.document.mark_dirty()
            self._refresh_document_ui()
            self.status_label.text = f"Layer {property_name} updated"
        except (TypeError, ValueError, AttributeError) as exc:
            self._show_error(f"Could not update layer:\n{exc}")

    def _on_layer_name_submitted(self, value: str) -> None:
        layer = self._selected_layer()
        if layer is None:
            return
        new_name = str(value).strip()
        if not new_name or new_name == layer.name:
            self._refresh_document_ui()
            return
        try:
            self.commands.execute(TileMapLayerRenameCommand(self._selected_tilemap_editor_model().tilemap, layer, new_name))
            self.document.mark_dirty()
            self._refresh_document_ui()
            self.status_label.text = f"Renamed layer to {new_name}"
        except (TypeError, ValueError) as exc:
            self.layer_name_input.set_text(layer.name, emit=False)
            self._show_error(f"Could not rename layer:\n{exc}")

    def _on_layer_role_changed(self, _index: int, value: str | None) -> None:
        if value is None:
            return
        role = normalize_layer_role(value)
        self._set_layer_property("role", role)

    def _on_layer_render_submitted(self, value: str) -> None:
        try:
            render_layer = int(str(value).strip())
        except ValueError:
            self._refresh_document_ui()
            self.status_label.text = "Render Layer must be an integer"
            return
        self._set_layer_property("render_layer", render_layer)

    def _on_layer_opacity_submitted(self, value: str) -> None:
        try:
            opacity = max(0.0, min(1.0, float(str(value).strip())))
        except ValueError:
            self._refresh_document_ui()
            self.status_label.text = "Opacity must be a number from 0 to 1"
            return
        self._set_layer_property("opacity", opacity)

    def _set_tilemap_tool(self, tool: str) -> None:
        tool = str(tool).lower()
        if tool not in {"select", "paint", "erase", "fill"}:
            raise ValueError(f"Unknown TileMap tool: {tool}")
        self.tilemap_tool = tool
        self._tilemap_drag_cells = None
        self._refresh_tool_ui()
        self.status_label.text = f"TileMap tool: {tool.title()}"

    def _set_angled_2d_projection(self) -> None:
        model = self._selected_tilemap_editor_model()
        if model is None:
            self.status_label.text = "No configured TileMap selected"
            return
        if model.tilemap.projection is TileProjection.ANGLED_2D:
            self.status_label.text = "TileMap is already Angled 2D"
            return
        self.commands.execute(TileMapProjectionCommand(model.node, TileProjection.ANGLED_2D))
        self.document.mark_dirty()
        self._refresh_document_ui()
        self.status_label.text = "TileMap projection set to Angled 2D"

    def _on_tile_selected(self, index: int, _label: str | None) -> None:
        model = self._selected_tilemap_editor_model()
        if model is None:
            return
        try:
            model.set_selected_tile(index)
        except (IndexError, ValueError) as exc:
            self.status_label.text = str(exc)
            return
        self.tile_input.set_text(str(index), emit=False)
        self.status_label.text = f"Selected Tile {index}"

    def _on_layer_selected(self, index: int, _label: str | None) -> None:
        model = self._selected_tilemap_editor_model()
        if model is None or not (0 <= index < len(model.layer_names)):
            return
        model.set_active_layer(model.layer_names[index])
        self._refresh_document_ui()
        self.status_label.text = f"Active layer: {model.active_layer_name}"

    def _read_tile_id(self, model) -> bool:
        try:
            model.set_selected_tile(int(self.tile_input.text.strip()))
        except (TypeError, ValueError, IndexError) as exc:
            self.status_label.text = f"Invalid Tile ID: {exc}"
            return False
        return True

    def _apply_tilemap_command(self, command: TileMapPaintCommand) -> None:
        if not command.edits:
            self.status_label.text = "TileMap: no cells changed"
            return
        self.commands.execute(command)
        self.document.mark_dirty()
        self._refresh_document_ui()
        self.status_label.text = command.label

    def _viewport_mouse_centered(self) -> tuple[float, float]:
        mouse_x, mouse_y = self.game.input.mouse_position
        return (
            float(mouse_x) - float(self.game.renderer.width) * 0.5,
            float(mouse_y) - float(self.game.renderer.height) * 0.5,
        )

    def _mouse_inside_viewport_canvas(self) -> bool:
        if not hasattr(self, "viewport_canvas"):
            return False
        return self.viewport_canvas.contains_point(*self._viewport_mouse_centered())

    def _tilemap_cell_under_mouse(self, model):
        mouse_x, mouse_y = self._viewport_mouse_centered()
        center_x, center_y = self.viewport_canvas.calculate_position()
        world_x, world_y = self.viewport_state.screen_to_world(mouse_x, mouse_y, center_x, center_y)
        return model.cell_from_world(world_x, world_y)

    def _update_tilemap_input(self) -> None:
        if self._any_dialog_open():
            self._tilemap_drag_cells = None
            self._tilemap_hover_cell = None
            return
        model = self._selected_tilemap_editor_model()
        if model is None or not model.layer_names:
            self._tilemap_drag_cells = None
            self._tilemap_hover_cell = None
            return
        input_manager = self.game.input
        if input_manager.key_pressed("p"):
            self._set_tilemap_tool("paint")
        elif input_manager.key_pressed("x"):
            self._set_tilemap_tool("erase")
        elif input_manager.key_pressed("b"):
            self._set_tilemap_tool("fill")
        self._tilemap_hover_cell = self._tilemap_cell_under_mouse(model) if self._mouse_inside_viewport_canvas() else None
        if input_manager.key_pressed("escape"):
            self._tilemap_drag_cells = None
            return
        if self.tilemap_tool == "select":
            return
        if self._tilemap_drag_cells is not None:
            if input_manager.mouse_down("left"):
                cell = self._tilemap_cell_under_mouse(model)
                if cell is not None and cell not in self._tilemap_drag_cells:
                    self._tilemap_drag_cells.append(cell)
            if input_manager.mouse_released("left"):
                cells = self._tilemap_drag_cells
                self._tilemap_drag_cells = None
                if self.tilemap_tool == "erase" or self._read_tile_id(model):
                    command = model.erase_command(cells) if self.tilemap_tool == "erase" else model.paint_command(cells)
                    self._apply_tilemap_command(command)
            return
        if not self._mouse_inside_viewport_canvas() or input_manager.mouse_down("middle"):
            return
        if input_manager.mouse_pressed("left"):
            if self.tilemap_tool == "fill":
                if self._read_tile_id(model):
                    self._apply_tilemap_command(model.fill_command())
            else:
                cell = self._tilemap_cell_under_mouse(model)
                if cell is not None:
                    self._tilemap_drag_cells = [cell]

    def _update_viewport_input(self) -> None:
        if self.game.renderer is None or self._any_dialog_open():
            return
        input_manager = self.game.input
        if input_manager.key_pressed("home"):
            self.viewport_state.reset()
            self.status_label.text = "Viewport reset"
        if not self._mouse_inside_viewport_canvas():
            return
        mouse_x, mouse_y = self._viewport_mouse_centered()
        center_x, center_y = self.viewport_canvas.calculate_position()
        if input_manager.mouse_down("middle"):
            delta_x, delta_y = input_manager.mouse_delta
            self.viewport_state.pan_screen_delta(delta_x, delta_y)
        _wheel_x, wheel_y = input_manager.wheel
        if wheel_y:
            self.viewport_state.zoom_at(mouse_x, mouse_y, center_x, center_y, 1.15 ** float(wheel_y))

    # ----------------------------------------------------------
    # Refresh, undo and layout
    # ----------------------------------------------------------

    def _refresh_tool_ui(self) -> None:
        model = self._selected_tilemap_editor_model()
        enabled = model is not None and bool(model.layer_names)
        for control in (self.select_button, self.paint_button, self.erase_button, self.fill_button, self.projection_button, self.tile_input):
            control.enabled = enabled
        for control in (
            self.layer_name_input,
            self.layer_role_dropdown,
            self.layer_visible_checkbox,
            self.layer_enabled_checkbox,
            self.layer_render_input,
            self.layer_opacity_input,
            self.layer_y_sort_checkbox,
        ):
            control.enabled = enabled
        if model is None:
            self.tool_label.text = "No configured TileMap"
            self.layer_list.set_items([])
            self.tile_palette.set_tileset(None)
            self.info_label.text = "No TileMap asset selected.\nChoose a tileset image to begin."
            self.tileset_path_label.text = "No tileset selected"
            self.layer_name_input.set_text("", emit=False)
            self.layer_render_input.set_text("", emit=False)
            self.layer_opacity_input.set_text("", emit=False)
            self.layer_role_hint.text = "Select a layer to edit its role and properties."
            return
        layer = model.active_layer
        self.layer_name_input.set_text(layer.name, emit=False)
        self.layer_render_input.set_text(str(layer.render_layer), emit=False)
        self.layer_opacity_input.set_text(f"{layer.opacity:.2f}", emit=False)
        self.layer_visible_checkbox.set_checked(layer.visible, emit=False)
        self.layer_enabled_checkbox.set_checked(layer.enabled, emit=False)
        self.layer_y_sort_checkbox.set_checked(layer.y_sort, emit=False)
        role = normalize_layer_role(layer.role, name=layer.name)
        role_index = LAYER_ROLES.index(role) if role in LAYER_ROLES else 0
        self.layer_role_dropdown.set_selected_index(role_index, emit=False)
        role_hints = {
            "ground": "Base walkable/world surface.",
            "decoration": "Visual decoration without gameplay collision.",
            "objects": "Gameplay objects and interactables.",
            "foreground": "Rendered in front of actors.",
            "background": "Rendered behind the ground.",
            "collision": "Used by TileMap collision queries.",
            "trigger": "Used by trigger/teleport/interaction queries.",
            "navigation": "Used for navigation and pathfinding data.",
            "custom": "Custom-purpose layer.",
        }
        self.layer_role_hint.text = role_hints.get(role, role_hints["custom"])
        self.tool_label.text = f"Tool: {self.tilemap_tool.title()}  |  Projection: {model.tilemap.projection.value}"
        self.layer_list.set_items(
            [f"{layer.name}  [{normalize_layer_role(layer.role, name=layer.name).title()}]" for layer in model.tilemap.layers]
        )
        if model.active_layer_name in model.layer_names:
            self.layer_list.set_selected_index(model.layer_names.index(model.active_layer_name), emit=False)
        self.tile_palette.set_tileset(model.tileset, model.node.texture)
        selected = model.selected_tile if model.selected_tile is not None else 0
        if model.tileset.tile_count:
            self.tile_palette.set_selected_index(min(selected, model.tileset.tile_count - 1), emit=False)
        self.tile_input.set_text(str(selected), emit=False)
        self.map_width_input.set_text(str(model.tilemap.width), emit=False)
        self.map_height_input.set_text(str(model.tilemap.height), emit=False)
        self.tile_width_input.set_text(str(model.tilemap.tile_width), emit=False)
        self.tile_height_input.set_text(str(model.tilemap.tile_height), emit=False)
        self.gap_x_input.set_text(str(model.tileset.spacing_x), emit=False)
        self.gap_y_input.set_text(str(model.tileset.spacing_y), emit=False)
        self.margin_x_input.set_text(str(model.tileset.margin_x), emit=False)
        self.margin_y_input.set_text(str(model.tileset.margin_y), emit=False)
        self.tileset_path_label.text = model.tileset.texture_asset or "No tileset selected"
        self.info_label.text = (
            f"Map: {model.tilemap.name or self.document.display_name}\n"
            f"Grid: {model.tilemap.width} x {model.tilemap.height}  |  "
            f"{model.tilemap.tile_width} x {model.tilemap.tile_height}\n"
            f"Projection: {model.tilemap.projection.value}\n"
            f"Layers: {len(model.layer_names)}"
        )

    def _refresh_document_ui(self) -> None:
        if not hasattr(self, "status_label"):
            return
        self.document_label.text = f"{self.document.title}  |  {self.project_path.name}"
        self.viewport_subtitle.text = f"Editing: {self.document.display_name}"
        self._refresh_tool_ui()
        self.undo_button.enabled = self.commands.can_undo
        self.redo_button.enabled = self.commands.can_redo

    def _on_selection_changed(self, node, _previous) -> None:
        if node is not None and not isinstance(node, TileMapNode):
            self.selection.clear()
        self._refresh_document_ui()

    def undo(self) -> None:
        if self.commands.undo() is not None:
            self.document.mark_dirty()
            self._refresh_document_ui()
            self.status_label.text = "Undo"

    def redo(self) -> None:
        if self.commands.redo() is not None:
            self.document.mark_dirty()
            self._refresh_document_ui()
            self.status_label.text = "Redo"

    def _any_dialog_open(self) -> bool:
        return any(
            bool(getattr(getattr(self, name, None), "is_open", False))
            for name in (
                "new_map_dialog",
                "open_dialog",
                "save_dialog",
                "tileset_dialog",
                "tileset_setup_dialog",
                "unsaved_dialog",
                "error_dialog",
            )
        )

    def update(self, delta_time: float) -> None:
        super().update(delta_time)
        self._sync_layout()
        self._update_viewport_input()
        self._update_tilemap_input()

    def render(self, renderer) -> None:
        self._sync_layout()
        super().render(renderer)

    def _sync_layout(self) -> None:
        renderer = self.game.renderer
        if renderer is None:
            return
        width, height = float(renderer.width), float(renderer.height)
        if (width, height) == self._last_size:
            return
        self._last_size = (width, height)
        self.background.size = (width, height)
        self.background.anchor = (0.5, 0.5)
        self.background.pivot = (0.5, 0.5)
        self.toolbar.size = (width, self.TOOLBAR_HEIGHT)
        self.toolbar.anchor = (0.5, 0.0)
        self.toolbar.pivot = (0.5, 0.0)
        self.toolbar.position = (0.0, self.TOOLBAR_HEIGHT / 2.0)
        self.status_bar.size = (width, self.STATUS_HEIGHT)
        self.status_bar.anchor = (0.5, 1.0)
        self.status_bar.pivot = (0.5, 1.0)
        self.status_bar.position = (0.0, -self.STATUS_HEIGHT / 2.0)
        body_top = self.TOOLBAR_HEIGHT + self.GAP
        body_bottom = height - self.STATUS_HEIGHT - self.GAP
        body_height = max(0.0, body_bottom - body_top)
        bottom_h = min(self.BOTTOM_HEIGHT, max(130.0, body_height * 0.30))
        upper_h = max(0.0, body_height - bottom_h - self.GAP)
        left_w = min(self.LEFT_WIDTH, width * 0.24)
        right_w = min(self.RIGHT_WIDTH, width * 0.26)
        center_w = max(0.0, width - left_w - right_w - self.GAP * 2.0)
        for panel, panel_w, x in (
            (self.map_panel, left_w, left_w / 2.0),
            (self.viewport, center_w, left_w + self.GAP + center_w / 2.0),
            (self.info_panel, right_w, left_w + self.GAP + center_w + self.GAP + right_w / 2.0),
        ):
            panel.size = (panel_w, upper_h)
            panel.anchor = (0.0, 0.0)
            panel.pivot = (0.0, 0.0)
            panel.position = (x, body_top + upper_h / 2.0)
        self.bottom_dock.size = (width, bottom_h)
        self.bottom_dock.anchor = (0.0, 0.0)
        self.bottom_dock.pivot = (0.0, 0.0)
        self.bottom_dock.position = (width / 2.0, body_top + upper_h + self.GAP + bottom_h / 2.0)
        self._sync_toolbar(width)
        self._sync_map_panel(left_w, upper_h)
        self._sync_viewport(center_w, upper_h)
        self._sync_info_panel(right_w, upper_h)
        self._sync_tileset_setup_layout()
        self._sync_bottom(width, bottom_h)
        self.brand_label.position = (16.0, 0.0)
        self.document_label.position = (-16.0, 0.0)
        self.status_label.position = (12.0, 0.0)
        self.version_label.position = (-12.0, 0.0)

    def _sync_toolbar(self, width: float) -> None:
        del width
        buttons = (
            (self.new_button, 66.0), (self.open_button, 74.0), (self.save_button, 72.0),
            (self.save_as_button, 92.0), (self.tileset_button, 78.0), (self.scene_editor_button, 112.0),
            (self.undo_button, 72.0), (self.redo_button, 72.0),
        )
        x = 105.0
        for button, button_width in buttons:
            button.size = (button_width, 34.0)
            button.anchor = (0.0, 0.5)
            button.pivot = (0.5, 0.5)
            button.position = (x + button_width / 2.0, 0.0)
            x += button_width + 6.0

    def _sync_map_panel(self, width: float, height: float) -> None:
        self.map_title.position = (12.0, 12.0)
        self.layer_list.size = (max(0.0, width - 16.0), max(0.0, height - 120.0))
        self.layer_list.anchor = (0.0, 0.0)
        self.layer_list.pivot = (0.5, 0.5)
        self.layer_list.position = (width / 2.0, 48.0 + max(0.0, height - 120.0) / 2.0)
        button_y = height - 54.0
        button_width = max(0.0, width / 2.0 - 18.0)
        for button, x in (
            (self.add_layer_button, width * 0.25),
            (self.remove_layer_button, width * 0.75),
        ):
            button.size = (button_width, 28.0)
            button.anchor = (0.0, 0.0)
            button.pivot = (0.5, 0.5)
            button.position = (x, button_y)
        self.layer_hint.position = (12.0, height - 20.0)

    def _sync_viewport(self, width: float, height: float) -> None:
        self.viewport_canvas.size = (width, height)
        self.viewport_canvas.anchor = (0.5, 0.5)
        self.viewport_canvas.pivot = (0.5, 0.5)
        self.viewport_canvas.position = (0.0, 0.0)
        self.viewport_title.position = (12.0, 10.0)
        self.viewport_subtitle.position = (12.0, 30.0)
        self.viewport_controls.anchor = (1.0, 0.0)
        self.viewport_controls.pivot = (1.0, 0.0)
        self.viewport_controls.position = (-12.0, 10.0)
        self.tool_label.position = (12.0, 54.0)
        y = 78.0
        row_x = 12.0
        for button, button_width in (
            (self.select_button, 70.0), (self.paint_button, 70.0),
            (self.erase_button, 70.0), (self.fill_button, 70.0),
        ):
            button.size = (button_width, 30.0)
            button.anchor = (0.0, 0.0)
            button.pivot = (0.5, 0.5)
            button.position = (row_x + button_width / 2.0, y)
            row_x += button_width + 6.0
        self.tile_input.size = (78.0, 30.0)
        self.tile_input.anchor = (0.0, 0.0)
        self.tile_input.pivot = (0.5, 0.5)
        self.tile_input.position = (row_x + 39.0, y)
        self.projection_button.size = (105.0, 30.0)
        self.projection_button.anchor = (1.0, 0.0)
        self.projection_button.pivot = (0.5, 0.5)
        self.projection_button.position = (width - 66.0, y)

    def _sync_info_panel(self, width: float, height: float) -> None:
        del height
        content_width = max(0.0, width - 24.0)
        column_gap = 8.0
        half_width = max(0.0, (content_width - column_gap) / 2.0)
        left_column_center = 12.0 + half_width / 2.0
        right_column_center = width - 12.0 - half_width / 2.0
        self.info_title.position = (12.0, 12.0)
        self.info_label.position = (12.0, 48.0)
        self.info_label.size = (content_width, 70.0)

        self.layer_inspector_title.position = (12.0, 116.0)
        self.layer_name_label.position = (12.0, 140.0)
        self.layer_name_input.size = (content_width, 30.0)
        self.layer_name_input.anchor = (0.0, 0.0)
        self.layer_name_input.pivot = (0.5, 0.5)
        self.layer_name_input.position = (width / 2.0, 162.0)
        self.layer_role_label.position = (12.0, 184.0)
        self.layer_role_dropdown.size = (content_width, 30.0)
        self.layer_role_dropdown.anchor = (0.0, 0.0)
        self.layer_role_dropdown.pivot = (0.5, 0.5)
        self.layer_role_dropdown.position = (width / 2.0, 206.0)
        for checkbox, x in (
            (self.layer_visible_checkbox, left_column_center),
            (self.layer_enabled_checkbox, right_column_center),
        ):
            checkbox.size = (half_width, 30.0)
            checkbox.anchor = (0.0, 0.0)
            checkbox.pivot = (0.5, 0.5)
            checkbox.position = (x, 248.0)
        self.layer_render_label.position = (12.0, 278.0)
        self.layer_render_input.size = (half_width, 30.0)
        self.layer_render_input.anchor = (0.0, 0.0)
        self.layer_render_input.pivot = (0.5, 0.5)
        self.layer_render_input.position = (left_column_center, 300.0)
        self.layer_opacity_label.position = (12.0 + half_width + column_gap, 278.0)
        self.layer_opacity_input.size = (half_width, 30.0)
        self.layer_opacity_input.anchor = (0.0, 0.0)
        self.layer_opacity_input.pivot = (0.5, 0.5)
        self.layer_opacity_input.position = (right_column_center, 300.0)
        self.layer_y_sort_checkbox.size = (half_width, 30.0)
        self.layer_y_sort_checkbox.anchor = (0.0, 0.0)
        self.layer_y_sort_checkbox.pivot = (0.5, 0.5)
        self.layer_y_sort_checkbox.position = (left_column_center, 338.0)
        self.layer_role_hint.position = (12.0, 370.0)

        self.config_title.position = (12.0, 392.0)
        self.tileset_path_label.position = (12.0, 418.0)
        for button, x in (
            (self.apply_tileset_button, left_column_center),
            (self.apply_map_button, right_column_center),
        ):
            button.size = (half_width, 28.0)
            button.anchor = (0.0, 0.0)
            button.pivot = (0.5, 0.5)
            button.position = (x, 448.0)
        fields = (
            ("MapWidth", self.map_width_input), ("MapHeight", self.map_height_input),
            ("TileWidth", self.tile_width_input), ("TileHeight", self.tile_height_input),
            ("GapX", self.gap_x_input), ("GapY", self.gap_y_input),
            ("MarginX", self.margin_x_input), ("MarginY", self.margin_y_input),
        )
        for index, (name, input_node) in enumerate(fields):
            column = index % 2
            row = index // 2
            x = (
                left_column_center
                if column == 0
                else right_column_center
            )
            label_x = (
                12.0
                if column == 0
                else 12.0 + half_width + column_gap
            )
            # Labels sit above their controls. A 38px row step keeps the
            # four setting rows readable without letting the last row fall
            # behind the bottom dock at the default window size.
            y = 466.0 + row * 38.0
            label = self._config_labels[name]
            label.position = (label_x, y)
            input_node.size = (half_width, 24.0)
            input_node.anchor = (0.0, 0.0)
            input_node.pivot = (0.5, 0.5)
            input_node.position = (x, y + 20.0)

    def _sync_tileset_setup_layout(self) -> None:
        """Arrange the tileset setup wizard inside its dialog content."""
        content = self.tileset_setup_dialog.content
        width, height = content.size
        if width <= 0.0 or height <= 0.0:
            width, height = (644.0, 268.0)
        padding = 16.0
        column_gap = 18.0
        column_width = max(0.0, (width - padding * 2.0 - column_gap) / 2.0)
        left = -width / 2.0 + padding
        right = left + column_width + column_gap
        top = -height / 2.0 + 12.0

        for label in (
            self.tileset_setup_info,
            self.tileset_setup_error,
            self.tileset_setup_summary,
            self.tileset_setup_tile_width_label,
            self.tileset_setup_tile_height_label,
            self.tileset_setup_gap_x_label,
            self.tileset_setup_gap_y_label,
            self.tileset_setup_margin_x_label,
            self.tileset_setup_margin_y_label,
        ):
            label.anchor = (0.0, 0.0)
            label.pivot = (0.0, 0.0)

        self.tileset_setup_info.position = (left, top)
        fields = (
            ("tile_width", self.tileset_setup_tile_width_label),
            ("tile_height", self.tileset_setup_tile_height_label),
            ("gap_x", self.tileset_setup_gap_x_label),
            ("gap_y", self.tileset_setup_gap_y_label),
            ("margin_x", self.tileset_setup_margin_x_label),
            ("margin_y", self.tileset_setup_margin_y_label),
        )
        for index, (name, label) in enumerate(fields):
            column = index % 2
            row = index // 2
            column_left = left if column == 0 else right
            center = column_left + column_width / 2.0
            y = top + 46.0 + row * 52.0
            label.position = (column_left, y)
            input_node = self.tileset_setup_inputs[name]
            input_node.size = (column_width, 30.0)
            input_node.anchor = (0.0, 0.0)
            input_node.pivot = (0.5, 0.5)
            input_node.position = (center, y + 22.0)

        self.tileset_setup_summary.position = (left, top + 216.0)
        self.tileset_setup_error.position = (left, top + 240.0)

    def _sync_bottom(self, width: float, height: float) -> None:
        self.palette_title.position = (12.0, 12.0)
        self.tile_palette.size = (max(0.0, width - 24.0), max(0.0, height - 54.0))
        self.tile_palette.anchor = (0.0, 0.0)
        self.tile_palette.pivot = (0.5, 0.5)
        self.tile_palette.position = (width / 2.0, 54.0 + max(0.0, height - 54.0) / 2.0)
        self.palette_hint.position = (width - 12.0, 18.0)
        self.palette_hint.anchor = (1.0, 0.0)
        self.palette_hint.pivot = (1.0, 0.0)


class TileMapEditorApp(Game):
    """Nexora application wrapper for the standalone TileMap editor."""

    def __init__(self, *, project_path: str | Path | None = None, tilemap_path: str | Path | None = None) -> None:
        self.tilemap_project_path = resolve_project_path(project_path)
        self.tilemap_asset_path = tilemap_path
        super().__init__(
            project_name="NexoraTileMapEditor",
            title=f"Nexora TileMap Editor - {self.tilemap_project_path.name}",
            width=1440,
            height=900,
            resizable=True,
            editor_mode=True,
        )
        self.tilemap_editor_scene = None

    def initialize(self) -> None:
        # AssetManager defaults to the process working directory. The
        # standalone editor can open another project, so bind asset loading
        # to that project's assets directory before any TileMap is created.
        if self.engine is not None:
            assets_root = self.tilemap_project_path / "assets"
            self.engine.assets.root = (
                assets_root if assets_root.is_dir() else self.tilemap_project_path
            )
        icon_path = self.tilemap_project_path / "assets" / "icon.png"
        if self.window is not None and icon_path.is_file():
            try:
                self.window.set_icon(icon_path)
            except Exception:
                # A missing/unsupported platform icon must not prevent the
                # editor itself from starting.
                pass
        document = EditorDocument()
        scene = TileMapEditorScene(
            self,
            self.tilemap_project_path,
            document=document,
            selection=SelectionService(),
        )
        self.tilemap_editor_scene = scene
        self.scene = scene
        scene._create_new_map()
        if self.tilemap_asset_path is not None:
            scene.open_path(self.tilemap_asset_path)


def run_tilemap_editor(
    project_path: str | Path | None = None,
    tilemap_path: str | Path | None = None,
) -> int:
    try:
        app = TileMapEditorApp(project_path=project_path, tilemap_path=tilemap_path)
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"[Nexora TileMap Editor] {exc}")
        return 2
    app.run()
    return 0


__all__ = ["TileMapEditorApp", "TileMapEditorScene", "run_tilemap_editor"]
