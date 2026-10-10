from __future__ import annotations

"""Standalone TileMap authoring application with its own UI toolkit."""

from pathlib import Path

from nexora.editor.commands import CommandStack
from nexora.editor.model import EditorProjectContext
from nexora.editor.standalone_app import StandaloneEditorApp, run_standalone_editor
from nexora.editor.ui import (
    Button,
    CheckBox,
    Dropdown,
    FormLayout,
    ListBox,
    Menu,
    Rect,
    TextField,
    centered_rect,
    draw_outline,
    draw_rect,
    draw_text,
    layout_equal_row,
    layout_fixed_row,
    render_document_title,
    render_editor_shell,
    render_form_label,
    render_section_title,
    render_status_bar,
)
from nexora.editor.base_editor import EditorBaseScene
from .tilemap_document import TileMapDocumentMixin
from .tilemap_layers import TileMapLayerMixin
from .tilemap_painting import TileMapPaintingMixin
from .tilemap_rendering import TileMapRenderingMixin
from nexora.tilemap import TileMap, TileSet
from nexora.tilemap.tile_layer import LAYER_ROLES


class StandaloneTileMapEditorScene(
    TileMapDocumentMixin,
    TileMapLayerMixin,
    TileMapPaintingMixin,
    TileMapRenderingMixin,
    EditorBaseScene,
):
    """A renderer/input driven editor that does not use Nexora UI nodes."""

    MODAL_CLOSE_STATUS = "Ready"

    TOOLBAR_HEIGHT = EditorBaseScene.TOOLBAR_HEIGHT
    STATUS_HEIGHT = EditorBaseScene.STATUS_HEIGHT
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

        self.browser_mode = "tileset"
        self.browser_root = self.project_path
        self.browser_path = self._asset_root()
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
        self._set_menus([self.file_menu, self.tilemap_menu, self.help_menu])
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

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------







    # ------------------------------------------------------------------
    # Tileset browser and setup wizard
    # ------------------------------------------------------------------









    # ------------------------------------------------------------------
    # Layer inspector
    # ------------------------------------------------------------------










    def _quit_editor(self) -> None:
        self.game.stop()

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







    # ------------------------------------------------------------------
    # Editing
    # ------------------------------------------------------------------







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
        layout_fixed_row(
            (self.file_menu, self.tilemap_menu, self.help_menu),
            (88.0, 108.0, 86.0),
            x=105.0,
            y=5.0,
            height=38.0,
            gap=7.0,
        )
        self.layer_list.rect = Rect(self.left_panel.x + 10.0, self.left_panel.y + 48.0, self.left_panel.width - 20.0, self.left_panel.height - 126.0)
        layer_button_width = self.left_panel.width - 20.0
        layout_equal_row(
            (self.move_layer_up_button, self.move_layer_down_button),
            x=self.left_panel.x + 10.0,
            y=self.left_panel.y + self.left_panel.height - 86.0,
            width=layer_button_width,
            height=32.0,
            gap=10.0,
        )
        layout_equal_row(
            (self.add_layer_button, self.remove_layer_button),
            x=self.left_panel.x + 10.0,
            y=self.left_panel.y + self.left_panel.height - 48.0,
            width=layer_button_width,
            height=32.0,
            gap=10.0,
        )
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
        inspector_form = FormLayout(
            x=inner_x,
            y=self.right_panel.y,
            width=inner_w,
            columns=2,
            column_gap=8.0,
            control_height=34.0,
            label_gap=0.0,
        )
        half = inspector_form.column_width
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
        setup_form = FormLayout(
            x=window.x + 18.0,
            y=window.y + 112.0,
            width=626.0,
            columns=2,
            column_gap=26.0,
            row_step=54.0,
            control_height=30.0,
            label_gap=18.0,
        )
        for index, name in enumerate(labels):
            self.setup_fields[name].rect = setup_form.control_rect(
                index // 2,
                index % 2,
            )
        self.setup_cancel_button.rect = Rect(window.x + window.width - 244.0, window.y + window.height - 52.0, 108.0, 32.0)
        self.setup_apply_button.rect = Rect(window.x + window.width - 124.0, window.y + window.height - 52.0, 108.0, 32.0)
        info_window = centered_rect((width, height), 660.0, 380.0)
        self.info_close_button.rect = Rect(info_window.x + info_window.width - 126.0, info_window.y + info_window.height - 52.0, 108.0, 32.0)





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





    def _render_main_ui(self, renderer, viewport_size) -> None:
        width, height = viewport_size
        render_editor_shell(
            renderer,
            viewport_size,
            self.theme,
            toolbar_height=self.TOOLBAR_HEIGHT,
            status_height=self.STATUS_HEIGHT,
            panels=(
                (self.left_panel, self.theme.panel),
                (self.right_panel, self.theme.panel),
                (self.bottom_panel, self.theme.panel_dark),
            ),
            outline_rects=(self.left_panel, self.viewport, self.right_panel, self.bottom_panel),
        )
        render_document_title(
            renderer,
            viewport_size,
            self.theme,
            self.document_name,
            dirty=self.dirty,
            scale=0.62,
        )
        render_section_title(renderer, viewport_size, self.theme, self.left_panel, "Map Layers")
        render_section_title(
            renderer,
            viewport_size,
            self.theme,
            self.viewport,
            "2D TileMap View",
            y_offset=12.0,
        )
        draw_text(renderer, "P Paint   X Erase   B Fill   MMB Pan   Wheel Zoom   Home Reset", self.viewport.x + self.viewport.width - 12.0, self.viewport.y + 16.0, viewport_size, scale=0.48, color=self.theme.muted, align="right")
        render_section_title(
            renderer,
            viewport_size,
            self.theme,
            self.bottom_panel,
            "Tile Palette",
            y_offset=12.0,
        )
        render_status_bar(
            renderer,
            viewport_size,
            self.theme,
            self.status,
            "Nexora Standalone TileMap Editor",
            status_height=self.STATUS_HEIGHT,
        )

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
            render_section_title(renderer, viewport_size, self.theme, self.right_panel, "TileMap")
            draw_text(renderer, f"Map: {self.document_name}\nGrid: {self.tilemap.width} x {self.tilemap.height} | {self.tilemap.tile_width} x {self.tilemap.tile_height}\nProjection: {self.tilemap.projection.value}\nLayers: {self.tilemap.layer_count}", self.right_panel.x + 12.0, self.right_panel.y + 42.0, viewport_size, scale=0.50, color=self.theme.muted)
            render_section_title(renderer, viewport_size, self.theme, self.right_panel, "Map Size", y_offset=104.0, scale=0.62)
            render_form_label(renderer, viewport_size, self.theme, "Width", self.right_panel.x + 12.0, self.right_panel.y + 122.0)
            render_form_label(renderer, viewport_size, self.theme, "Height", self.right_panel.x + self.right_panel.width / 2.0 + 4.0, self.right_panel.y + 122.0)
            render_section_title(renderer, viewport_size, self.theme, self.right_panel, "Selected Layer", y_offset=226.0, scale=0.62)
            render_form_label(renderer, viewport_size, self.theme, "Name", self.right_panel.x + 12.0, self.right_panel.y + 246.0)
            render_form_label(renderer, viewport_size, self.theme, "Role", self.right_panel.x + 12.0, self.right_panel.y + 298.0)
            render_form_label(renderer, viewport_size, self.theme, "Render Layer", self.right_panel.x + 12.0, self.right_panel.y + 392.0)
            render_form_label(renderer, viewport_size, self.theme, "Opacity", self.right_panel.x + self.right_panel.width / 2.0 + 4.0, self.right_panel.y + 392.0)
        self._render_palette(renderer, viewport_size)

    def _render_browser(self, renderer, viewport_size) -> None:
        title = "Choose Tileset Image" if self.browser_mode == "tileset" else "Open TileMap Asset"
        if self.browser_mode == "map_save":
            title = "Save TileMap Asset"
        self._render_file_dialog(renderer, viewport_size, title=title)

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
                self._render_info_dialog(renderer, viewport_size, width=660.0, height=380.0, line_step=38.0)
            elif self.modal == "setup":
                self._render_setup(renderer, viewport_size)


class StandaloneTileMapEditorApp(StandaloneEditorApp[StandaloneTileMapEditorScene]):
    """Application wrapper for the from-scratch TileMap editor."""

    PROJECT_NAME = "NexoraStandaloneTileMapEditor"
    WINDOW_TITLE = "Nexora TileMap Editor"
    WINDOW_WIDTH = 1440
    WINDOW_HEIGHT = 900
    ERROR_PREFIX = "Nexora Standalone TileMap Editor"

    def __init__(self, *, project_path: str | Path | None = None, tilemap_path: str | Path | None = None) -> None:
        self.tilemap_asset_path = tilemap_path
        super().__init__(project_path=project_path)
        self.tilemap_project_path = self.project_path
        self.tilemap_project_context = self.project_context

    def create_editor_scene(self) -> StandaloneTileMapEditorScene:
        return StandaloneTileMapEditorScene(
            self,
            self.project_path,
            self.project_context,
        )

    def after_editor_scene_created(self, scene: StandaloneTileMapEditorScene) -> None:
        if self.tilemap_asset_path is None:
            return
        asset_path = self.project_context.resolve_project_file(
            self.tilemap_asset_path,
            include_assets=True,
        )
        scene._load_asset(asset_path)


def run_standalone_tilemap_editor(project_path: str | Path | None = None, tilemap_path: str | Path | None = None) -> int:
    return run_standalone_editor(
        StandaloneTileMapEditorApp,
        project_path=project_path,
        tilemap_path=tilemap_path,
    )


__all__ = [
    "StandaloneTileMapEditorApp",
    "StandaloneTileMapEditorScene",
    "run_standalone_tilemap_editor",
]
