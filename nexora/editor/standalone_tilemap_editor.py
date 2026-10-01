from __future__ import annotations

"""Standalone TileMap authoring application with its own UI toolkit."""

from pathlib import Path

from nexora import Game
from nexora.editor.commands import CommandStack, TileMapCellEdit, TileMapPaintCommand
from nexora.editor.model import EditorProjectContext
from nexora.editor.ui import (
    Button,
    CheckBox,
    Dropdown,
    ListBox,
    Menu,
    Rect,
    TextField,
    UITheme,
    FileBrowserModel,
    centered_rect,
    close_other_menus,
    draw_outline,
    draw_rect,
    draw_text,
    rgba,
    sync_browser_list,
)
from nexora.editor.app import resolve_project_path
from nexora.scene import Scene
from nexora.tilemap import TILEMAP_ASSET_SUFFIX, TileMap, TileMapAsset, TileProjection, TileSet
from nexora.tilemap.tile_layer import LAYER_ROLES, normalize_layer_role


class StandaloneTileMapEditorScene(Scene):
    """A renderer/input driven editor that does not use Nexora UI nodes."""

    TOOLBAR_HEIGHT = 58.0
    STATUS_HEIGHT = 30.0
    LEFT_WIDTH = 246.0
    RIGHT_WIDTH = 330.0
    BOTTOM_HEIGHT = 188.0
    GAP = 1.0

    def __init__(
        self,
        game,
        project_path: Path,
        project_context: EditorProjectContext | None = None,
    ) -> None:
        super().__init__("StandaloneTileMapEditor")
        self.game = game
        self.project_context = project_context or EditorProjectContext.from_path(project_path)
        self.project_path = self.project_context.root
        self.theme = UITheme()
        self.viewport = Rect(0.0, 0.0, 1.0, 1.0)
        self.left_panel = Rect(0.0, 0.0, 1.0, 1.0)
        self.right_panel = Rect(0.0, 0.0, 1.0, 1.0)
        self.bottom_panel = Rect(0.0, 0.0, 1.0, 1.0)
        self._layout_size = (-1.0, -1.0)

        self.tilemap: TileMap | None = None
        self.tileset: TileSet | None = None
        self.texture = None
        self.document_path: Path | None = None
        self.document_name = "Untitled"
        self.dirty = False
        self.pending_tileset_path: Path | None = None
        self.tileset_image_size: tuple[int, int] | None = None

        self.commands = CommandStack()
        self.active_layer_name: str | None = None
        self.selected_tile = 0
        self.tool = "paint"
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.zoom = 1.0
        self.stroke_layer = None
        self.stroke_tile = None
        self.stroke_edits: dict[tuple[int, int], int] = {}
        self.status = "Ready"

        self.modal: str | None = None
        self.browser_mode = "tileset"
        self.browser_root = self.project_path
        self.browser_path = self._asset_root()
        self.browser_entries: list[Path] = []
        self.file_browser = FileBrowserModel()
        self.browser_list = ListBox(Rect(0, 0, 1, 1), self._browser_selected)
        self.browser_cancel_button = Button(Rect(0, 0, 1, 1), "Cancel", self._close_modal)
        self.browser_save_button = Button(Rect(0, 0, 1, 1), "Save", self._save_from_browser)
        self.browser_name = TextField(Rect(0, 0, 1, 1), "", "File name")

        self.setup_fields = {
            "tile_width": TextField(Rect(0, 0, 1, 1), "32"),
            "tile_height": TextField(Rect(0, 0, 1, 1), "32"),
            "gap_x": TextField(Rect(0, 0, 1, 1), "0"),
            "gap_y": TextField(Rect(0, 0, 1, 1), "0"),
            "margin_x": TextField(Rect(0, 0, 1, 1), "0"),
            "margin_y": TextField(Rect(0, 0, 1, 1), "0"),
        }
        for field in self.setup_fields.values():
            field.on_change = lambda _value: self._update_setup_summary()
        self.setup_apply_button = Button(Rect(0, 0, 1, 1), "Apply Tileset", self._apply_setup)
        self.setup_cancel_button = Button(Rect(0, 0, 1, 1), "Cancel", self._close_modal)
        self.setup_error = ""
        self.setup_summary = ""
        self.info_title = ""
        self.info_lines: tuple[str, ...] = ()
        self.info_close_button = Button(Rect(0, 0, 1, 1), "Close", self._close_modal)

        self.layer_list = ListBox(Rect(0, 0, 1, 1), self._layer_selected)
        self.layer_list.row_height = 34.0
        self.layer_list.row_action = self._toggle_layer_visibility
        self.layer_list.row_action_state = self._layer_is_visible
        self.layer_name = TextField(Rect(0, 0, 1, 1), "")
        self.layer_name.on_submit = lambda _value: self._rename_active_layer()
        self.layer_role = Dropdown(Rect(0, 0, 1, 1), tuple(role.title() for role in LAYER_ROLES), on_change=self._role_changed)
        self.layer_visible = CheckBox(Rect(0, 0, 1, 1), "Visible", True, lambda value: self._set_layer_property("visible", value))
        self.layer_enabled = CheckBox(Rect(0, 0, 1, 1), "Enabled", True, lambda value: self._set_layer_property("enabled", value))
        self.layer_render = TextField(Rect(0, 0, 1, 1), "0")
        self.layer_render.on_submit = lambda _value: self._submit_layer_number("render_layer")
        self.layer_opacity = TextField(Rect(0, 0, 1, 1), "1.0")
        self.layer_opacity.on_submit = lambda _value: self._submit_layer_number("opacity")
        self.layer_y_sort = CheckBox(Rect(0, 0, 1, 1), "Y-Sort", False, lambda value: self._set_layer_property("y_sort", value))
        self.map_width = TextField(Rect(0, 0, 1, 1), "16")
        self.map_height = TextField(Rect(0, 0, 1, 1), "16")
        self.apply_map_size_button = Button(Rect(0, 0, 1, 1), "Apply Map Size", self._apply_map_size)
        self.add_layer_button = Button(Rect(0, 0, 1, 1), "+ Layer", self._add_layer)
        self.remove_layer_button = Button(Rect(0, 0, 1, 1), "- Layer", self._remove_layer)
        self.move_layer_up_button = Button(Rect(0, 0, 1, 1), "↑ Up", self._move_layer_up)
        self.move_layer_down_button = Button(Rect(0, 0, 1, 1), "↓ Down", self._move_layer_down)

        self.file_menu = Menu(
            Rect(0, 0, 1, 1),
            "File",
            [("New", self.new_map), ("Open", self.open_map), ("Save", self.save_map), ("Save As", self.save_map_as), ("Exit", self._quit_editor)],
        )
        self.tilemap_menu = Menu(
            Rect(0, 0, 1, 1),
            "Tilemap",
            [("Load Tileset", self.open_tileset_browser), ("Add Layer", self._add_layer), ("Remove Layer", self._remove_layer), ("Move Layer Up", self._move_layer_up), ("Move Layer Down", self._move_layer_down), ("Undo", self.undo), ("Redo", self.redo)],
        )
        self.help_menu = Menu(
            Rect(0, 0, 1, 1),
            "Help",
            [("Keyboard Shortcuts", self._show_help_dialog), ("TileMap Workflow", self._show_workflow_dialog), ("About Nexora", self._show_about_dialog), ("Version 0.10", self._show_about_dialog)],
        )
        self.menus = [self.file_menu, self.tilemap_menu, self.help_menu]
        for menu in self.menus:
            menu.on_open = self._menu_opened
        self.tool_buttons = [
            Button(Rect(0, 0, 1, 1), "Select", lambda: self._set_tool("select")),
            Button(Rect(0, 0, 1, 1), "Paint", lambda: self._set_tool("paint")),
            Button(Rect(0, 0, 1, 1), "Erase", lambda: self._set_tool("erase")),
            Button(Rect(0, 0, 1, 1), "Fill", lambda: self._set_tool("fill")),
        ]

        self.new_map()

    # ------------------------------------------------------------------
    # Project and asset paths
    # ------------------------------------------------------------------

    def _asset_root(self) -> Path:
        return self.project_context.assets_root

    def _asset_relative(self, path: Path) -> str:
        return self.project_context.relative_asset(path, root=self._asset_root())

    def _asset_path(self, relative: str | Path) -> Path:
        return self.project_context.resolve_asset(relative)

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def new_map(self) -> None:
        self.tilemap = TileMap(
            name="Untitled",
            width=16,
            height=16,
            tile_width=32,
            tile_height=32,
            projection=TileProjection.ANGLED_2D,
        )
        self.tilemap.create_layer("ground", role="ground")
        self.tileset = None
        self.texture = None
        self.document_path = None
        self.document_name = "Untitled"
        self.pending_tileset_path = None
        self.active_layer_name = "ground"
        self.selected_tile = 0
        self.commands.clear()
        self.dirty = False
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.status = "New TileMap"
        self._refresh_layer_controls()
        self._refresh_map_controls()

    def open_map(self) -> None:
        self._open_browser("map_open")

    def save_map(self) -> None:
        if self.document_path is None:
            self.save_map_as()
            return
        self._save_asset(self.document_path)

    def save_map_as(self) -> None:
        self._open_browser("map_save")
        self.browser_name.set_text(f"{self.document_name}{TILEMAP_ASSET_SUFFIX}")

    def _save_asset(self, path: Path) -> None:
        if self.tilemap is None or self.tileset is None or not self.tileset.texture_asset:
            self.status = "Choose and configure a tileset before saving."
            return
        saved = TileMapAsset.from_components(self.tilemap, self.tileset, name=self.document_name).save(path)
        self.document_path = saved
        self.tilemap.name = self.document_name
        self.dirty = False
        self.status = f"Saved {saved.name}"

    def _load_asset(self, path: Path) -> None:
        try:
            asset = TileMapAsset.load(path)
            self.tilemap, self.tileset = asset.build()
            if not self.tileset.texture_asset:
                raise ValueError("TileMap asset has no tileset texture.")
            texture_path = self._asset_path(self.tileset.texture_asset)
            self.texture = self.game.engine.assets.texture(texture_path)
            self.document_path = path.resolve()
            self.document_name = asset.name
            self.active_layer_name = self.tilemap.layer_names[0] if self.tilemap.layer_names else None
            self.commands.clear()
            self.dirty = False
            self.status = f"Opened {path.name}"
            self._refresh_layer_controls()
            self._refresh_map_controls()
        except Exception as exc:
            self.status = f"Could not open TileMap: {exc}"

    # ------------------------------------------------------------------
    # Tileset browser and setup wizard
    # ------------------------------------------------------------------

    def open_tileset_browser(self) -> None:
        self._open_browser("tileset")

    def _open_browser(self, mode: str) -> None:
        self.modal = "browser"
        self.browser_mode = mode
        self.browser_root = self.project_path
        extensions = (
            (".png", ".jpg", ".jpeg", ".bmp", ".webp")
            if mode == "tileset"
            else (TILEMAP_ASSET_SUFFIX,)
        )
        self.file_browser.open(
            self.project_path,
            start=self._asset_root(),
            extensions=extensions,
        )
        self.browser_path = self.file_browser.path
        self.browser_name.set_text("")
        self._refresh_browser()

    def _refresh_browser(self) -> None:
        self.file_browser.refresh()
        self.browser_path = self.file_browser.path
        self.browser_entries = list(self.file_browser.entries)
        sync_browser_list(self.file_browser, self.browser_list)

    def _browser_selected(self, index: int) -> None:
        path = self.file_browser.select(index)
        self._refresh_browser()
        if path is None:
            return
        if self.browser_mode == "tileset":
            self._begin_tileset_setup(path)
        elif self.browser_mode == "map_save":
            # Save As must never open an existing asset.  Selecting one in
            # the browser only chooses its filename; the Save button then
            # performs the actual overwrite.
            self.browser_name.set_text(path.name)
            self.status = f"Save as {path.name}"
        else:
            self._load_asset(path)
            self._close_modal()

    def _browser_up(self) -> None:
        if self.file_browser.go_up():
            self._refresh_browser()

    def _save_from_browser(self) -> None:
        name = self.browser_name.text.strip() or f"{self.document_name}{TILEMAP_ASSET_SUFFIX}"
        if not name.lower().endswith(TILEMAP_ASSET_SUFFIX):
            name += TILEMAP_ASSET_SUFFIX
        self._save_asset(self.browser_path / name)
        self._close_modal()

    def _begin_tileset_setup(self, path: Path) -> None:
        try:
            image = self.game.engine.assets.image(path)
        except Exception as exc:
            self.status = f"Could not read image: {exc}"
            return
        self.pending_tileset_path = path.resolve()
        self.tileset_image_size = (int(image.width), int(image.height))
        self.modal = "setup"
        self.setup_error = ""
        for name, value in (
            ("tile_width", self.tilemap.tile_width if self.tilemap else 32),
            ("tile_height", self.tilemap.tile_height if self.tilemap else 32),
            ("gap_x", 0),
            ("gap_y", 0),
            ("margin_x", 0),
            ("margin_y", 0),
        ):
            self.setup_fields[name].set_text(str(value))
        self._update_setup_summary()

    def _setup_int(self, name: str, default: int = 0) -> int:
        try:
            return int(self.setup_fields[name].text.strip())
        except (TypeError, ValueError):
            return default

    def _update_setup_summary(self) -> None:
        if self.tileset_image_size is None:
            self.setup_summary = ""
            return
        image_width, image_height = self.tileset_image_size
        tile_width = self._setup_int("tile_width", 32)
        tile_height = self._setup_int("tile_height", 32)
        gap_x = self._setup_int("gap_x", 0)
        gap_y = self._setup_int("gap_y", 0)
        margin_x = self._setup_int("margin_x", 0)
        margin_y = self._setup_int("margin_y", 0)
        usable_width = image_width - margin_x * 2
        usable_height = image_height - margin_y * 2
        if tile_width <= 0 or tile_height <= 0 or gap_x < 0 or gap_y < 0 or usable_width <= 0 or usable_height <= 0:
            self.setup_summary = "Invalid values."
            return
        columns = (usable_width + gap_x) // (tile_width + gap_x)
        rows = (usable_height + gap_y) // (tile_height + gap_y)
        exact = (
            columns > 0
            and rows > 0
            and columns * tile_width + max(0, columns - 1) * gap_x == usable_width
            and rows * tile_height + max(0, rows - 1) * gap_y == usable_height
        )
        self.setup_summary = f"Image: {image_width} x {image_height} px   |   Grid: {columns} x {rows} tiles" if exact else "Grid does not fit the image exactly."

    def _apply_setup(self) -> None:
        if self.pending_tileset_path is None or self.tilemap is None or self.tileset_image_size is None:
            return
        image_width, image_height = self.tileset_image_size
        tile_width = self._setup_int("tile_width", 32)
        tile_height = self._setup_int("tile_height", 32)
        gap_x = self._setup_int("gap_x", 0)
        gap_y = self._setup_int("gap_y", 0)
        margin_x = self._setup_int("margin_x", 0)
        margin_y = self._setup_int("margin_y", 0)
        usable_width = image_width - margin_x * 2
        usable_height = image_height - margin_y * 2
        if tile_width <= 0 or tile_height <= 0 or gap_x < 0 or gap_y < 0 or usable_width <= 0 or usable_height <= 0:
            self.setup_error = "Tile size, gap and margin values are invalid."
            return
        columns = (usable_width + gap_x) // (tile_width + gap_x)
        rows = (usable_height + gap_y) // (tile_height + gap_y)
        expected_width = columns * tile_width + max(0, columns - 1) * gap_x
        expected_height = rows * tile_height + max(0, rows - 1) * gap_y
        if columns <= 0 or rows <= 0 or expected_width != usable_width or expected_height != usable_height:
            self.setup_error = "Grid does not fit. Adjust Tile Size, Gap or Margin."
            return
        try:
            asset_path = self._asset_relative(self.pending_tileset_path)
            self.tileset = TileSet(
                name=self.pending_tileset_path.stem,
                columns=columns,
                rows=rows,
                tile_width=tile_width,
                tile_height=tile_height,
                texture_asset=asset_path,
                spacing_x=gap_x,
                spacing_y=gap_y,
                margin_x=margin_x,
                margin_y=margin_y,
            )
            self.tilemap.tile_width = tile_width
            self.tilemap.tile_height = tile_height
            self.texture = self.game.engine.assets.texture(self.pending_tileset_path)
            self.dirty = True
            self.modal = None
            self.status = f"Tileset loaded: {columns} x {rows} tiles"
        except Exception as exc:
            self.setup_error = str(exc)

    # ------------------------------------------------------------------
    # Layer inspector
    # ------------------------------------------------------------------

    def _active_layer(self):
        if self.tilemap is None or self.active_layer_name is None:
            return None
        try:
            return self.tilemap.require_layer(self.active_layer_name)
        except KeyError:
            return None

    def _refresh_layer_controls(self) -> None:
        if self.tilemap is None:
            self.layer_list.set_items([])
            return
        self.layer_list.set_items([
            f"{layer.name} [{normalize_layer_role(layer.role, name=layer.name).title()}]"
            for layer in self.tilemap.layers
        ])
        if self.active_layer_name in self.tilemap.layer_names:
            self.layer_list.selected = self.tilemap.layer_names.index(self.active_layer_name)
        layer = self._active_layer()
        if layer is None:
            return
        self.layer_name.set_text(layer.name)
        self.layer_role.selected = LAYER_ROLES.index(normalize_layer_role(layer.role, name=layer.name))
        self.layer_visible.checked = layer.visible
        self.layer_enabled.checked = layer.enabled
        self.layer_render.set_text(str(layer.render_layer))
        self.layer_opacity.set_text(f"{layer.opacity:.2f}")
        self.layer_y_sort.checked = layer.y_sort

    def _layer_selected(self, index: int) -> None:
        if self.tilemap is None or not (0 <= index < len(self.tilemap.layers)):
            return
        self.active_layer_name = self.tilemap.layers[index].name
        self._refresh_layer_controls()

    def _add_layer(self) -> None:
        if self.tilemap is None:
            return
        base = "Layer"
        index = 1
        while f"{base} {index}" in self.tilemap:
            index += 1
        self.tilemap.create_layer(f"{base} {index}", role="custom")
        self.active_layer_name = f"{base} {index}"
        self.dirty = True
        self._refresh_layer_controls()

    def _remove_layer(self) -> None:
        if self.tilemap is None or self.active_layer_name is None or self.tilemap.layer_count <= 1:
            return
        index = self.tilemap.layer_index(self.active_layer_name)
        self.tilemap.remove_layer(self.active_layer_name)
        self.active_layer_name = self.tilemap.layers[max(0, index - 1)].name
        self.dirty = True
        self._refresh_layer_controls()

    def _layer_is_visible(self, index: int) -> bool:
        return bool(self.tilemap is not None and 0 <= index < self.tilemap.layer_count and self.tilemap.layers[index].visible)

    def _toggle_layer_visibility(self, index: int) -> None:
        if self.tilemap is None or not (0 <= index < self.tilemap.layer_count):
            return
        layer = self.tilemap.layers[index]
        layer.visible = not layer.visible
        self.dirty = True
        self.status = f"Layer {layer.name}: {'visible' if layer.visible else 'hidden'}"
        self._refresh_layer_controls()

    def _move_layer_up(self) -> None:
        if self.tilemap is None or self.active_layer_name is None:
            return
        self.tilemap.move_layer_down(self.active_layer_name)
        self.dirty = True
        self._refresh_layer_controls()
        self.status = f"Layer moved up: {self.active_layer_name}"

    def _move_layer_down(self) -> None:
        if self.tilemap is None or self.active_layer_name is None:
            return
        self.tilemap.move_layer_up(self.active_layer_name)
        self.dirty = True
        self._refresh_layer_controls()
        self.status = f"Layer moved down: {self.active_layer_name}"

    def _menu_opened(self, active_menu: Menu) -> None:
        close_other_menus(self.menus, active_menu)

    def _quit_editor(self) -> None:
        self.game.stop()

    def _open_info_dialog(self, title: str, lines: tuple[str, ...]) -> None:
        self.info_title = title
        self.info_lines = lines
        self.modal = "info"

    def _show_help_dialog(self) -> None:
        self._open_info_dialog(
            "Keyboard Shortcuts",
            (
                "P  Paint tiles",
                "X  Erase tiles",
                "B  Fill the active layer",
                "MMB  Pan the viewport",
                "Mouse wheel  Zoom in or out",
                "Home  Reset the viewport",
            ),
        )

    def _show_workflow_dialog(self) -> None:
        self._open_info_dialog(
            "TileMap Workflow",
            (
                "1. Load a tileset image",
                "2. Configure tile size, gap and margin",
                "3. Create and arrange layers",
                "4. Paint the map and assign layer roles",
                "5. Save it as a .ntmap asset",
            ),
        )

    def _show_about_dialog(self) -> None:
        self._open_info_dialog(
            "About Nexora",
            (
                "Nexora Standalone TileMap Editor",
                "Version 0.10",
                "A portable editor for Nexora .ntmap assets.",
            ),
        )

    def _refresh_map_controls(self) -> None:
        if self.tilemap is None:
            return
        self.map_width.set_text(str(self.tilemap.width))
        self.map_height.set_text(str(self.tilemap.height))

    def _apply_map_size(self) -> None:
        if self.tilemap is None:
            return
        try:
            width = max(1, min(4096, int(self.map_width.text.strip())))
            height = max(1, min(4096, int(self.map_height.text.strip())))
        except ValueError:
            self.status = "Invalid map size."
            self._refresh_map_controls()
            return
        if (width, height) == (self.tilemap.width, self.tilemap.height):
            self.status = "Map size unchanged."
            return

        old_map = self.tilemap
        resized = TileMap(
            name=old_map.name,
            width=width,
            height=height,
            tile_width=old_map.tile_width,
            tile_height=old_map.tile_height,
            projection=old_map.projection,
        )
        for old_layer in old_map.layers:
            new_layer = resized.create_layer(
                old_layer.name,
                visible=old_layer.visible,
                enabled=old_layer.enabled,
                opacity=old_layer.opacity,
                render_layer=old_layer.render_layer,
                y_sort=old_layer.y_sort,
                role=old_layer.role,
            )
            copy_width = min(old_map.width, width)
            copy_height = min(old_map.height, height)
            for y in range(copy_height):
                for x in range(copy_width):
                    tile_id = old_layer.get_tile(x, y)
                    if tile_id >= 0:
                        new_layer.set_tile(x, y, tile_id)
        self.tilemap = resized
        self.commands.clear()
        self.dirty = True
        self._refresh_layer_controls()
        self._refresh_map_controls()
        self.status = f"Map resized to {width} x {height}"

    def _rename_active_layer(self) -> None:
        layer = self._active_layer()
        name = self.layer_name.text.strip()
        if layer is None or not name or name == layer.name:
            return
        try:
            self.tilemap.rename_layer(layer, name)
            self.active_layer_name = name
            self.dirty = True
            self._refresh_layer_controls()
        except Exception as exc:
            self.status = str(exc)

    def _role_changed(self, index: int, _value: str) -> None:
        if not (0 <= index < len(LAYER_ROLES)):
            return
        self._set_layer_property("role", LAYER_ROLES[index])

    def _set_layer_property(self, name: str, value) -> None:
        layer = self._active_layer()
        if layer is None:
            return
        if name == "role":
            value = normalize_layer_role(value, name=layer.name)
        setattr(layer, name, value)
        self.dirty = True
        self._refresh_layer_controls()

    def _submit_layer_number(self, name: str) -> None:
        layer = self._active_layer()
        if layer is None:
            return
        try:
            value = int(self.layer_render.text) if name == "render_layer" else max(0.0, min(1.0, float(self.layer_opacity.text)))
            setattr(layer, name, value)
            self.dirty = True
            self._refresh_layer_controls()
        except ValueError:
            self.status = f"Invalid {name}."

    # ------------------------------------------------------------------
    # Editing
    # ------------------------------------------------------------------

    def _set_tool(self, tool: str) -> None:
        self.tool = str(tool)
        self.status = f"Tool: {self.tool.title()}"

    def _paint_cell(self, cell: tuple[int, int], tile_id: int) -> None:
        layer = self._active_layer()
        if layer is None or self.tilemap is None or not self.tilemap.contains(*cell):
            return
        if cell not in self.stroke_edits:
            self.stroke_edits[cell] = layer.get_tile(*cell)
        if tile_id < 0:
            layer.clear_tile(*cell)
        else:
            layer.set_tile(*cell, tile_id)

    def _finish_stroke(self) -> None:
        layer = self.stroke_layer
        if layer is None:
            return
        edits = [TileMapCellEdit(x, y, before, layer.get_tile(x, y)) for (x, y), before in self.stroke_edits.items()]
        command = TileMapPaintCommand(layer, edits, label="Paint Tiles" if self.stroke_tile >= 0 else "Erase Tiles")
        if command.edits:
            self.commands.execute(command)
            self.dirty = True
        self.stroke_layer = None
        self.stroke_tile = None
        self.stroke_edits.clear()

    def _fill_layer(self) -> None:
        layer = self._active_layer()
        if layer is None or self.tileset is None:
            return
        edits = [TileMapCellEdit(x, y, layer.get_tile(x, y), self.selected_tile) for y in range(layer.height) for x in range(layer.width)]
        command = TileMapPaintCommand(layer, edits, label="Fill Layer")
        if command.edits:
            self.commands.execute(command)
            self.dirty = True

    def undo(self) -> None:
        if self.commands.undo() is not None:
            self.dirty = True
            self.status = "Undo"

    def redo(self) -> None:
        if self.commands.redo() is not None:
            self.dirty = True
            self.status = "Redo"

    # ------------------------------------------------------------------
    # Layout and input
    # ------------------------------------------------------------------

    def _layout(self) -> tuple[float, float]:
        width = float(self.game.renderer.width)
        height = float(self.game.renderer.height)
        if (width, height) == self._layout_size:
            # Modal controls also depend on the current browser mode.  The
            # window size can stay unchanged while switching from the open
            # dialog to Save As, so they must be refreshed even when the
            # main layout is cached.
            self._layout_modal_controls(width, height)
            return width, height
        self._layout_size = (width, height)
        body_top = self.TOOLBAR_HEIGHT
        body_bottom = height - self.STATUS_HEIGHT
        body_height = max(0.0, body_bottom - body_top)
        bottom_height = min(self.BOTTOM_HEIGHT, max(150.0, body_height * 0.28))
        upper_height = max(0.0, body_height - bottom_height)
        left_width = min(self.LEFT_WIDTH, width * 0.25)
        right_width = min(self.RIGHT_WIDTH, width * 0.29)
        center_width = max(0.0, width - left_width - right_width)
        self.left_panel = Rect(0.0, body_top, left_width, upper_height)
        self.viewport = Rect(left_width, body_top, center_width, upper_height)
        self.right_panel = Rect(width - right_width, body_top, right_width, upper_height)
        self.bottom_panel = Rect(0.0, body_top + upper_height, width, bottom_height)
        self._layout_main_controls()
        self._layout_modal_controls(width, height)
        return width, height

    def _layout_main_controls(self) -> None:
        menu_x = 16.0
        menu_layout = ((self.file_menu, 88.0), (self.tilemap_menu, 108.0), (self.help_menu, 86.0))
        for menu, menu_width in menu_layout:
            menu.rect = Rect(menu_x, 9.0, menu_width, 40.0)
            menu_x += menu_width + 7.0
        self.layer_list.rect = Rect(self.left_panel.x + 10.0, self.left_panel.y + 48.0, self.left_panel.width - 20.0, self.left_panel.height - 126.0)
        self.add_layer_button.rect = Rect(self.left_panel.x + 10.0, self.left_panel.y + self.left_panel.height - 48.0, self.left_panel.width / 2.0 - 15.0, 32.0)
        self.remove_layer_button.rect = Rect(self.left_panel.x + self.left_panel.width / 2.0 + 5.0, self.left_panel.y + self.left_panel.height - 48.0, self.left_panel.width / 2.0 - 15.0, 32.0)
        self.move_layer_up_button.rect = Rect(self.left_panel.x + 10.0, self.left_panel.y + self.left_panel.height - 86.0, self.left_panel.width / 2.0 - 15.0, 32.0)
        self.move_layer_down_button.rect = Rect(self.left_panel.x + self.left_panel.width / 2.0 + 5.0, self.left_panel.y + self.left_panel.height - 86.0, self.left_panel.width / 2.0 - 15.0, 32.0)
        # Keep the editing tools below the viewport header, never in the top
        # menu bar, including after a window resize.
        tool_x = self.viewport.x + 12.0
        tool_y = max(self.TOOLBAR_HEIGHT + 42.0, self.viewport.y + 58.0)
        for button in self.tool_buttons:
            button.rect = Rect(tool_x, tool_y, 70.0, 30.0)
            tool_x += 76.0

        panel_x = self.right_panel.x
        inner_x = panel_x + 12.0
        inner_w = self.right_panel.width - 24.0
        half = (inner_w - 8.0) / 2.0
        self.layer_list.rect = self.layer_list.rect
        self.map_width.rect = Rect(inner_x, self.right_panel.y + 132.0, half, 34.0)
        self.map_height.rect = Rect(inner_x + half + 8.0, self.right_panel.y + 132.0, half, 34.0)
        self.apply_map_size_button.rect = Rect(inner_x, self.right_panel.y + 174.0, inner_w, 34.0)
        self.layer_name.rect = Rect(inner_x, self.right_panel.y + 254.0, inner_w, 34.0)
        self.layer_role.rect = Rect(inner_x, self.right_panel.y + 306.0, inner_w, 34.0)
        self.layer_visible.rect = Rect(inner_x, self.right_panel.y + 348.0, half, 30.0)
        self.layer_enabled.rect = Rect(inner_x + half + 8.0, self.right_panel.y + 348.0, half, 30.0)
        self.layer_render.rect = Rect(inner_x, self.right_panel.y + 400.0, half, 34.0)
        self.layer_opacity.rect = Rect(inner_x + half + 8.0, self.right_panel.y + 400.0, half, 34.0)
        self.layer_y_sort.rect = Rect(inner_x, self.right_panel.y + 442.0, half, 30.0)

    def _layout_modal_controls(self, width: float, height: float) -> None:
        """Lay out modal controls before input is processed.

        Rendering happens after ``update`` in the game loop, so assigning
        these rectangles only while drawing makes the first click land at
        stale coordinates.  Keeping all modal geometry here also makes the
        browser and setup wizard resize-safe.
        """
        browser_list_height = max(80.0, height - 294.0)
        window = Rect(150.0, 76.0, width - 300.0, height - 152.0)
        inner_x = window.x + 18.0
        inner_right = window.x + window.width - 18.0
        footer_y = window.y + window.height - 50.0
        self.browser_list.rect = Rect(inner_x, window.y + 78.0, max(220.0, window.width - 36.0), browser_list_height)
        if self.browser_mode == "map_save":
            self.browser_save_button.rect = Rect(inner_right - 100.0, footer_y, 100.0, 32.0)
            self.browser_cancel_button.rect = Rect(inner_right - 212.0, footer_y, 100.0, 32.0)
            self.browser_name.rect = Rect(inner_x, footer_y, max(180.0, self.browser_cancel_button.rect.x - inner_x - 14.0), 32.0)
        else:
            self.browser_cancel_button.rect = Rect(inner_right - 100.0, footer_y, 100.0, 32.0)

        window = Rect(width / 2.0 - 340.0, height / 2.0 - 215.0, 680.0, 430.0)
        labels = ("tile_width", "tile_height", "gap_x", "gap_y", "margin_x", "margin_y")
        left = window.x + 18.0
        top = window.y + 112.0
        for index, name in enumerate(labels):
            column = index % 2
            row = index // 2
            x = left + column * 326.0
            y = top + row * 54.0
            self.setup_fields[name].rect = Rect(x, y + 18.0, 300.0, 30.0)
        self.setup_cancel_button.rect = Rect(window.x + window.width - 244.0, window.y + window.height - 52.0, 108.0, 32.0)
        self.setup_apply_button.rect = Rect(window.x + window.width - 124.0, window.y + window.height - 52.0, 108.0, 32.0)
        info_window = centered_rect((width, height), 660.0, 380.0)
        self.info_close_button.rect = Rect(info_window.x + info_window.width - 126.0, info_window.y + info_window.height - 52.0, 108.0, 32.0)

    def _viewport_cell(self, mouse_x: float, mouse_y: float) -> tuple[int, int] | None:
        if self.tilemap is None or not self.viewport.contains(mouse_x, mouse_y):
            return None
        center_x = self.viewport.x + self.viewport.width / 2.0
        center_y = self.viewport.y + self.viewport.height / 2.0
        local_x = self.camera_x + (mouse_x - center_x) / max(self.zoom, 1e-6)
        local_y = self.camera_y + (mouse_y - center_y) / max(self.zoom, 1e-6)
        local_x += self.tilemap.pixel_width / 2.0
        local_y += self.tilemap.pixel_height / 2.0
        cell = self.tilemap.world_to_tile(local_x, local_y)
        return cell if self.tilemap.contains(*cell) else None

    def _update_viewport(self, input_manager, mouse_x: float, mouse_y: float) -> None:
        if self.modal is not None:
            return
        if input_manager.key_pressed("home"):
            self.camera_x = self.camera_y = 0.0
            self.zoom = 1.0
        if self.viewport.contains(mouse_x, mouse_y):
            _wheel_x, wheel_y = input_manager.wheel
            if wheel_y:
                self.zoom = max(0.15, min(6.0, self.zoom * (1.15 ** float(wheel_y))))
            if input_manager.mouse_down("middle"):
                dx, dy = input_manager.mouse_delta
                self.camera_x -= dx / max(self.zoom, 1e-6)
                self.camera_y -= dy / max(self.zoom, 1e-6)
            cell = self._viewport_cell(mouse_x, mouse_y)
            if self.tool == "fill" and input_manager.mouse_pressed("left") and cell is not None:
                self._fill_layer()
                return
            if self.tool in {"paint", "erase"}:
                left_held = input_manager.mouse_pressed("left") or input_manager.mouse_down("left")
                if left_held and cell is not None:
                    if self.stroke_layer is None:
                        self.stroke_layer = self._active_layer()
                        self.stroke_tile = self.selected_tile if self.tool == "paint" else -1
                    # Tile ID 0 is a valid tile and must not be treated as
                    # EMPTY_TILE while a drag is continued.
                    tile_id = self.stroke_tile if self.stroke_tile is not None else -1
                    self._paint_cell(cell, tile_id)
                if self.stroke_layer is not None and input_manager.mouse_released("left"):
                    self._finish_stroke()
            if self.tool == "select" and input_manager.mouse_pressed("left") and cell is not None:
                layer = self._active_layer()
                if layer is not None and layer.get_tile(*cell) >= 0:
                    self.selected_tile = layer.get_tile(*cell)

    def _focus_fields(self, fields: list[TextField], input_manager, mouse_x: float, mouse_y: float) -> None:
        if not input_manager.mouse_pressed("left"):
            return
        clicked = next((field for field in fields if field.rect.contains(mouse_x, mouse_y)), None)
        for field in fields:
            if field is not clicked:
                field.blur(input_manager)

    def _update_controls(self, controls: list, input_manager, mouse_x: float, mouse_y: float) -> None:
        fields = [control for control in controls if isinstance(control, TextField)]
        self._focus_fields(fields, input_manager, mouse_x, mouse_y)
        for control in controls:
            control.update(input_manager, mouse_x, mouse_y)

    def _palette_tile_at(self, mouse_x: float, mouse_y: float) -> int | None:
        if self.tileset is None or self.texture is None or not self.bottom_panel.contains(mouse_x, mouse_y):
            return None
        cell_size = 62.0
        columns = max(1, int((self.bottom_panel.width - 24.0) // cell_size))
        local_x = mouse_x - (self.bottom_panel.x + 12.0)
        local_y = mouse_y - (self.bottom_panel.y + 38.0)
        if local_x < 0.0 or local_y < 0.0:
            return None
        column = int(local_x // cell_size)
        row = int(local_y // cell_size)
        within_x = local_x - column * cell_size
        within_y = local_y - row * cell_size
        if within_x > cell_size - 4.0 or within_y > cell_size - 4.0:
            return None
        index = row * columns + column
        return index if 0 <= index < self.tileset.tile_count else None

    def _update_palette(self, input_manager, mouse_x: float, mouse_y: float) -> None:
        if input_manager.mouse_pressed("left"):
            tile_id = self._palette_tile_at(mouse_x, mouse_y)
            if tile_id is not None:
                self.selected_tile = tile_id
                self.tool = "paint"
                self.status = f"Selected tile {tile_id}"

    def update(self, delta_time: float) -> None:
        del delta_time
        width, height = self._layout()
        mouse_x, mouse_y = self.game.input.mouse_position
        if self.modal == "browser":
            controls = [self.browser_list, self.browser_cancel_button]
            if self.browser_mode == "map_save":
                controls.extend((self.browser_name, self.browser_save_button))
            self._update_controls(controls, self.game.input, mouse_x, mouse_y)
            return
        if self.modal == "info":
            self._update_controls([self.info_close_button], self.game.input, mouse_x, mouse_y)
            return
        if self.modal == "setup":
            controls = list(self.setup_fields.values()) + [self.setup_apply_button, self.setup_cancel_button]
            self._update_controls(controls, self.game.input, mouse_x, mouse_y)
            return
        menu_was_open = any(menu.open for menu in self.menus)
        self._update_controls(self.menus, self.game.input, mouse_x, mouse_y)
        if menu_was_open or any(menu.open for menu in self.menus):
            return
        controls = [self.layer_list, self.add_layer_button, self.remove_layer_button, self.move_layer_up_button, self.move_layer_down_button, *self.tool_buttons, self.layer_name, self.layer_role, self.layer_visible, self.layer_enabled, self.layer_render, self.layer_opacity, self.layer_y_sort, self.map_width, self.map_height, self.apply_map_size_button]
        self._update_controls(controls, self.game.input, mouse_x, mouse_y)
        if self.game.input.key_pressed("p"):
            self._set_tool("paint")
        elif self.game.input.key_pressed("x"):
            self._set_tool("erase")
        elif self.game.input.key_pressed("b"):
            self._set_tool("fill")
        self._update_palette(self.game.input, mouse_x, mouse_y)
        self._update_viewport(self.game.input, mouse_x, mouse_y)
        del width, height

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _renderer_point(self, screen_x: float, screen_y: float) -> tuple[float, float]:
        return (screen_x - self.game.renderer.width / 2.0, screen_y - self.game.renderer.height / 2.0)

    def _visible_cell_bounds(self) -> tuple[int, int, int, int]:
        """Return the map-cell rectangle currently visible in the viewport."""
        if self.tilemap is None:
            return (0, -1, 0, -1)
        center_x = self.viewport.x + self.viewport.width / 2.0
        center_y = self.viewport.y + self.viewport.height / 2.0
        zoom = max(self.zoom, 1e-6)
        corners = (
            (self.viewport.x, self.viewport.y),
            (self.viewport.x + self.viewport.width, self.viewport.y),
            (self.viewport.x, self.viewport.y + self.viewport.height),
            (self.viewport.x + self.viewport.width, self.viewport.y + self.viewport.height),
        )
        cells = []
        for screen_x, screen_y in corners:
            local_x = self.camera_x + (screen_x - center_x) / zoom
            local_y = self.camera_y + (screen_y - center_y) / zoom
            local_x += self.tilemap.pixel_width / 2.0
            local_y += self.tilemap.pixel_height / 2.0
            cells.append(self.tilemap.world_to_tile(local_x, local_y))
        min_x = max(0, min(cell[0] for cell in cells) - 1)
        max_x = min(self.tilemap.width - 1, max(cell[0] for cell in cells) + 1)
        min_y = max(0, min(cell[1] for cell in cells) - 1)
        max_y = min(self.tilemap.height - 1, max(cell[1] for cell in cells) + 1)
        return min_x, max_x, min_y, max_y

    def _render_map(self, renderer) -> None:
        if self.tilemap is None:
            return
        center_x = self.viewport.x + self.viewport.width / 2.0
        center_y = self.viewport.y + self.viewport.height / 2.0
        min_x, max_x, min_y, max_y = self._visible_cell_bounds()
        visible_layers = sorted(enumerate(self.tilemap.layers), key=lambda item: (item[1].render_layer, item[0]))
        for _index, layer in visible_layers:
            if not layer.visible or not layer.enabled:
                continue
            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    tile_id = layer.get_tile(x, y)
                    if tile_id < 0:
                        continue
                    local_x, local_y = self.tilemap.tile_to_world(x, y)
                    local_x -= self.tilemap.pixel_width / 2.0
                    local_y -= self.tilemap.pixel_height / 2.0
                    screen_x = center_x + (local_x - self.camera_x) * self.zoom
                    screen_y = center_y + (local_y - self.camera_y) * self.zoom
                    if not self.viewport.contains(screen_x, screen_y):
                        continue
                    draw_x, draw_y = self._renderer_point(screen_x, screen_y)
                    if self.texture is not None and self.tileset is not None and self.tileset.contains(tile_id):
                        renderer.sprite(self.texture, draw_x, draw_y, width=self.tilemap.tile_width * self.zoom, height=self.tilemap.tile_height * self.zoom, uv=self.tileset.uv(tile_id), alpha=max(0.0, min(1.0, layer.opacity)))
        # A full grid is useful at editing zoom levels but becomes an
        # expensive command storm when zoomed far out.  Visible cells are
        # already clipped above, and the grid is skipped when it is too small
        # to be useful visually.
        if self.zoom < 0.35:
            return
        grid_color = rgba((52, 59, 72, 150))
        if self.tilemap.projection is not TileProjection.ISOMETRIC:
            # The orthogonal/angled editor grid is made from shared boundary
            # lines.  Drawing one rectangle plus two lines per cell scales
            # badly on large empty maps (for example 160 x 16).
            map_left = center_x + (-self.tilemap.pixel_width / 2.0 - self.camera_x) * self.zoom
            map_top = center_y + (-self.tilemap.pixel_height / 2.0 - self.camera_y) * self.zoom
            tile_width = self.tilemap.tile_width * self.zoom
            tile_height = self.tilemap.tile_height * self.zoom
            viewport_left = self.viewport.x
            viewport_right = self.viewport.x + self.viewport.width
            viewport_top = self.viewport.y
            viewport_bottom = self.viewport.y + self.viewport.height
            line_min_x = max(viewport_left, map_left + min_x * tile_width)
            line_max_x = min(viewport_right, map_left + (max_x + 1) * tile_width)
            line_min_y = max(viewport_top, map_top + min_y * tile_height)
            line_max_y = min(viewport_bottom, map_top + (max_y + 1) * tile_height)
            if line_min_x > line_max_x or line_min_y > line_max_y:
                return
            for x in range(min_x, max_x + 2):
                screen_x = map_left + x * tile_width
                if viewport_left <= screen_x <= viewport_right:
                    draw_x, draw_top = self._renderer_point(screen_x, line_min_y)
                    _unused, draw_bottom = self._renderer_point(screen_x, line_max_y)
                    renderer.line(draw_x, draw_top, draw_x, draw_bottom, width=1.0, color=grid_color)
            for y in range(min_y, max_y + 2):
                screen_y = map_top + y * tile_height
                if viewport_top <= screen_y <= viewport_bottom:
                    draw_left, draw_y = self._renderer_point(line_min_x, screen_y)
                    draw_right, _unused = self._renderer_point(line_max_x, screen_y)
                    renderer.line(draw_left, draw_y, draw_right, draw_y, width=1.0, color=grid_color)
            return
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                local_x, local_y = self.tilemap.tile_to_world(x, y)
                local_x -= self.tilemap.pixel_width / 2.0
                local_y -= self.tilemap.pixel_height / 2.0
                screen_x = center_x + (local_x - self.camera_x) * self.zoom
                screen_y = center_y + (local_y - self.camera_y) * self.zoom
                if self.viewport.contains(screen_x, screen_y):
                    draw_x, draw_y = self._renderer_point(screen_x, screen_y)
                    renderer.rect(draw_x, draw_y, self.tilemap.tile_width * self.zoom, self.tilemap.tile_height * self.zoom, color=(0.2, 0.23, 0.28, 0.16), radius=0.0)
                    renderer.line(draw_x - self.tilemap.tile_width * self.zoom / 2.0, draw_y - self.tilemap.tile_height * self.zoom / 2.0, draw_x + self.tilemap.tile_width * self.zoom / 2.0, draw_y - self.tilemap.tile_height * self.zoom / 2.0, width=1.0, color=grid_color)
                    renderer.line(draw_x - self.tilemap.tile_width * self.zoom / 2.0, draw_y - self.tilemap.tile_height * self.zoom / 2.0, draw_x - self.tilemap.tile_width * self.zoom / 2.0, draw_y + self.tilemap.tile_height * self.zoom / 2.0, width=1.0, color=grid_color)

    def _render_palette(self, renderer, viewport_size) -> None:
        if self.tileset is None or self.texture is None:
            draw_text(renderer, "Choose a tileset image to begin.", self.bottom_panel.x + 16.0, self.bottom_panel.y + 48.0, viewport_size, scale=0.62, color=self.theme.muted)
            return
        cell_size = 62.0
        columns = max(1, int((self.bottom_panel.width - 24.0) // cell_size))
        for index in range(self.tileset.tile_count):
            column = index % columns
            row = index // columns
            x = self.bottom_panel.x + 12.0 + column * cell_size
            y = self.bottom_panel.y + 38.0 + row * cell_size
            if y + cell_size > self.bottom_panel.y + self.bottom_panel.height:
                break
            cell = Rect(x, y, cell_size - 4.0, cell_size - 4.0)
            draw_rect(renderer, cell, self.theme.selected if index == self.selected_tile else self.theme.panel_dark, viewport_size, radius=3.0)
            draw_outline(renderer, cell, self.theme.accent if index == self.selected_tile else self.theme.border, viewport_size)
            sx, sy = self._renderer_point(x + cell.width / 2.0, y + cell.height / 2.0)
            renderer.sprite(self.texture, sx, sy, width=cell.width - 12.0, height=cell.height - 12.0, uv=self.tileset.uv(index))

    def _render_main_ui(self, renderer, viewport_size) -> None:
        width, height = viewport_size
        draw_rect(renderer, Rect(0, 0, width, self.TOOLBAR_HEIGHT), self.theme.panel, viewport_size)
        draw_rect(renderer, self.left_panel, self.theme.panel, viewport_size)
        draw_rect(renderer, self.right_panel, self.theme.panel, viewport_size)
        draw_rect(renderer, self.bottom_panel, self.theme.panel_dark, viewport_size)
        draw_rect(renderer, Rect(0, height - self.STATUS_HEIGHT, width, self.STATUS_HEIGHT), self.theme.panel, viewport_size)
        for rect in (Rect(0, 0, width, self.TOOLBAR_HEIGHT), self.left_panel, self.viewport, self.right_panel, self.bottom_panel):
            draw_outline(renderer, rect, self.theme.border, viewport_size)

        draw_text(renderer, f"{self.document_name}{' *' if self.dirty else ''}", width - 16.0, 18.0, viewport_size, scale=0.62, color=self.theme.muted, align="right")
        draw_text(renderer, "Map Layers", self.left_panel.x + 12.0, self.left_panel.y + 14.0, viewport_size, scale=0.76)
        draw_text(renderer, "2D TileMap View", self.viewport.x + 12.0, self.viewport.y + 12.0, viewport_size, scale=0.76)
        draw_text(renderer, "P Paint   X Erase   B Fill   MMB Pan   Wheel Zoom   Home Reset", self.viewport.x + self.viewport.width - 12.0, self.viewport.y + 16.0, viewport_size, scale=0.48, color=self.theme.muted, align="right")
        draw_text(renderer, "Tile Palette", self.bottom_panel.x + 12.0, self.bottom_panel.y + 12.0, viewport_size, scale=0.76)
        draw_text(renderer, self.status, 12.0, height - self.STATUS_HEIGHT + 7.0, viewport_size, scale=0.56, color=self.theme.muted)
        draw_text(renderer, "Nexora Standalone TileMap Editor", width - 12.0, height - self.STATUS_HEIGHT + 7.0, viewport_size, scale=0.56, color=self.theme.muted, align="right")

        self.layer_list.render(renderer, viewport_size, self.theme)
        self.add_layer_button.render(renderer, viewport_size, self.theme)
        self.remove_layer_button.render(renderer, viewport_size, self.theme)
        self.move_layer_up_button.render(renderer, viewport_size, self.theme)
        self.move_layer_down_button.render(renderer, viewport_size, self.theme)
        for menu in self.menus:
            menu.render(renderer, viewport_size, self.theme)
        for button in self.tool_buttons:
            button.render(renderer, viewport_size, self.theme)
        for control in (self.map_width, self.map_height, self.apply_map_size_button, self.layer_name, self.layer_role, self.layer_visible, self.layer_enabled, self.layer_render, self.layer_opacity, self.layer_y_sort):
            control.render(renderer, viewport_size, self.theme)
        layer = self._active_layer()
        if layer is not None:
            draw_text(renderer, "TileMap", self.right_panel.x + 12.0, self.right_panel.y + 14.0, viewport_size, scale=0.76)
            draw_text(renderer, f"Map: {self.document_name}\nGrid: {self.tilemap.width} x {self.tilemap.height} | {self.tilemap.tile_width} x {self.tilemap.tile_height}\nProjection: {self.tilemap.projection.value}\nLayers: {self.tilemap.layer_count}", self.right_panel.x + 12.0, self.right_panel.y + 42.0, viewport_size, scale=0.50, color=self.theme.muted)
            draw_text(renderer, "Map Size", self.right_panel.x + 12.0, self.right_panel.y + 104.0, viewport_size, scale=0.62)
            draw_text(renderer, "Width", self.right_panel.x + 12.0, self.right_panel.y + 122.0, viewport_size, scale=0.44, color=self.theme.muted)
            draw_text(renderer, "Height", self.right_panel.x + self.right_panel.width / 2.0 + 4.0, self.right_panel.y + 122.0, viewport_size, scale=0.44, color=self.theme.muted)
            draw_text(renderer, "Selected Layer", self.right_panel.x + 12.0, self.right_panel.y + 226.0, viewport_size, scale=0.62)
            draw_text(renderer, "Name", self.right_panel.x + 12.0, self.right_panel.y + 246.0, viewport_size, scale=0.44, color=self.theme.muted)
            draw_text(renderer, "Role", self.right_panel.x + 12.0, self.right_panel.y + 298.0, viewport_size, scale=0.44, color=self.theme.muted)
            draw_text(renderer, "Render Layer", self.right_panel.x + 12.0, self.right_panel.y + 392.0, viewport_size, scale=0.44, color=self.theme.muted)
            draw_text(renderer, "Opacity", self.right_panel.x + self.right_panel.width / 2.0 + 4.0, self.right_panel.y + 392.0, viewport_size, scale=0.44, color=self.theme.muted)
        self._render_palette(renderer, viewport_size)

    def _render_browser(self, renderer, viewport_size) -> None:
        width, height = viewport_size
        draw_rect(renderer, Rect(0, 0, width, height), (0, 0, 0, 175), viewport_size)
        window = Rect(150.0, 76.0, width - 300.0, height - 152.0)
        draw_rect(renderer, window, self.theme.panel, viewport_size, radius=6.0)
        draw_outline(renderer, window, self.theme.border, viewport_size)
        title = "Choose Tileset Image" if self.browser_mode == "tileset" else "Open TileMap Asset"
        if self.browser_mode == "map_save":
            title = "Save TileMap Asset"
        draw_text(renderer, title, window.x + 18.0, window.y + 16.0, viewport_size, scale=0.80)
        draw_text(renderer, str(self.browser_path), window.x + 18.0, window.y + 50.0, viewport_size, scale=0.48, color=self.theme.muted)
        self.browser_list.render(renderer, viewport_size, self.theme)
        self.browser_cancel_button.render(renderer, viewport_size, self.theme)
        if self.browser_mode == "map_save":
            draw_text(renderer, "File name", window.x + 18.0, window.y + window.height - 72.0, viewport_size, scale=0.48, color=self.theme.muted)
            self.browser_name.render(renderer, viewport_size, self.theme)
            self.browser_save_button.render(renderer, viewport_size, self.theme)

    def _render_info_dialog(self, renderer, viewport_size) -> None:
        width, height = viewport_size
        draw_rect(renderer, Rect(0, 0, width, height), (0, 0, 0, 175), viewport_size)
        window = Rect(width / 2.0 - 330.0, height / 2.0 - 190.0, 660.0, 380.0)
        draw_rect(renderer, window, self.theme.panel, viewport_size, radius=6.0)
        draw_outline(renderer, window, self.theme.border, viewport_size)
        draw_text(renderer, self.info_title, window.x + 22.0, window.y + 20.0, viewport_size, scale=0.86)
        y = window.y + 78.0
        for line in self.info_lines:
            draw_text(renderer, line, window.x + 24.0, y, viewport_size, scale=0.64, color=self.theme.text)
            y += 38.0
        self.info_close_button.render(renderer, viewport_size, self.theme)

    def _render_setup(self, renderer, viewport_size) -> None:
        width, height = viewport_size
        draw_rect(renderer, Rect(0, 0, width, height), (0, 0, 0, 175), viewport_size)
        window = Rect(width / 2.0 - 340.0, height / 2.0 - 215.0, 680.0, 430.0)
        draw_rect(renderer, window, self.theme.panel, viewport_size, radius=6.0)
        draw_outline(renderer, window, self.theme.border, viewport_size)
        draw_text(renderer, "Tileset Setup", window.x + 18.0, window.y + 18.0, viewport_size, scale=0.80)
        image_size = self.tileset_image_size or (0, 0)
        draw_text(renderer, f"Image: {image_size[0]} x {image_size[1]} px\n{self._asset_relative(self.pending_tileset_path) if self.pending_tileset_path else ''}", window.x + 18.0, window.y + 58.0, viewport_size, scale=0.54, color=self.theme.muted)
        labels = (("Tile Width", "tile_width"), ("Tile Height", "tile_height"), ("Gap X", "gap_x"), ("Gap Y", "gap_y"), ("Margin X", "margin_x"), ("Margin Y", "margin_y"))
        left = window.x + 18.0
        top = window.y + 112.0
        col_width = 300.0
        for index, (label, name) in enumerate(labels):
            column = index % 2
            row = index // 2
            x = left + column * 326.0
            y = top + row * 54.0
            draw_text(renderer, label, x, y, viewport_size, scale=0.46, color=self.theme.muted)
            field = self.setup_fields[name]
            field.rect = Rect(x, y + 18.0, col_width, 30.0)
            field.render(renderer, viewport_size, self.theme)
        draw_text(renderer, self.setup_summary, window.x + 18.0, window.y + 286.0, viewport_size, scale=0.54, color=self.theme.warning if "does not" in self.setup_summary else self.theme.muted)
        if self.setup_error:
            draw_text(renderer, self.setup_error, window.x + 18.0, window.y + 316.0, viewport_size, scale=0.54, color=self.theme.error)
        self.setup_cancel_button.rect = Rect(window.x + window.width - 244.0, window.y + window.height - 52.0, 108.0, 32.0)
        self.setup_apply_button.rect = Rect(window.x + window.width - 124.0, window.y + window.height - 52.0, 108.0, 32.0)
        self.setup_cancel_button.render(renderer, viewport_size, self.theme)
        self.setup_apply_button.render(renderer, viewport_size, self.theme)

    def render(self, interpolation: float) -> None:
        del interpolation
        width, height = self._layout()
        renderer = self.game.renderer
        viewport_size = (width, height)
        # The viewport background belongs to the world pass.  Drawing it in
        # the overlay pass would cover every painted tile rendered before it.
        draw_rect(renderer, self.viewport, self.theme.background, viewport_size)
        self._render_map(renderer)
        with renderer.overlay_scope():
            self._render_main_ui(renderer, viewport_size)
            if self.modal == "browser":
                self._render_browser(renderer, viewport_size)
            elif self.modal == "info":
                self._render_info_dialog(renderer, viewport_size)
            elif self.modal == "setup":
                self._render_setup(renderer, viewport_size)

    def _close_modal(self) -> None:
        self.modal = None
        self.status = "Ready"


class StandaloneTileMapEditorApp(Game):
    """Application wrapper for the from-scratch TileMap editor."""

    def __init__(self, *, project_path: str | Path | None = None, tilemap_path: str | Path | None = None) -> None:
        self.tilemap_project_path = resolve_project_path(project_path)
        self.tilemap_project_context = EditorProjectContext.from_path(self.tilemap_project_path)
        self.tilemap_asset_path = tilemap_path
        super().__init__(
            project_name="NexoraStandaloneTileMapEditor",
            title=f"Nexora TileMap Editor - {self.tilemap_project_path.name}",
            width=1440,
            height=900,
            resizable=True,
            editor_mode=True,
        )
        self.editor_scene = None

    def initialize(self) -> None:
        if self.engine is not None:
            self.engine.assets.root = self.tilemap_project_context.assets_root
        icon_path = self.tilemap_project_context.icon_path
        if self.window is not None and icon_path.is_file():
            try:
                self.window.set_icon(icon_path)
            except Exception:
                pass
        scene = StandaloneTileMapEditorScene(
            self,
            self.tilemap_project_path,
            self.tilemap_project_context,
        )
        self.editor_scene = scene
        self.scene = scene
        if self.tilemap_asset_path is not None:
            raw_path = Path(self.tilemap_asset_path).expanduser()
            if raw_path.is_absolute():
                asset_path = raw_path
            else:
                candidates = (
                    self.tilemap_project_context.resolve_asset(raw_path),
                    self.tilemap_project_context.resolve_project_file(raw_path),
                    Path.cwd() / raw_path,
                )
                asset_path = next((candidate for candidate in candidates if candidate.is_file()), candidates[0])
            scene._load_asset(asset_path.resolve())


def run_standalone_tilemap_editor(project_path: str | Path | None = None, tilemap_path: str | Path | None = None) -> int:
    try:
        StandaloneTileMapEditorApp(project_path=project_path, tilemap_path=tilemap_path).run()
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"[Nexora Standalone TileMap Editor] {exc}")
        return 2
    return 0


__all__ = [
    "StandaloneTileMapEditorApp",
    "StandaloneTileMapEditorScene",
    "run_standalone_tilemap_editor",
]
