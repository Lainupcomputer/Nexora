from __future__ import annotations

from nexora.nodes.ui.ui_node import UINode
from nexora.tilemap import TileProjection

from .renderer import EditorViewportRenderer
from .state import EditorViewportState

class EditorViewportCanvas(UINode):
    """UI node responsible for rendering the editable scene preview."""

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)
        self.editor_scene = None
        self.grid_enabled = True
        self.grid_size = 32.0
        self.background = (0.055, 0.060, 0.070, 1.0)

    def _clip_rect(self, renderer) -> tuple[float, float, float, float]:
        # Renderer clip rectangles use Nexora's centered screen coordinate
        # system, exactly like UI/node draw coordinates.
        #
        # The GPU sprite/rect batches convert these centered coordinates to
        # SDL top-left pixel coordinates internally when creating the scissor
        # rectangle. Adding half the renderer size here would therefore apply
        # the conversion twice and move the scissor far to the bottom-right.
        #
        # That was why sprites existed, had a visible selection rectangle and
        # correct Inspector dimensions, but their texture itself was clipped
        # away in the editor viewport.
        del renderer

        cx, cy = self.calculate_position()
        width, height = self.size

        return (
            cx - width * 0.5,
            cy - height * 0.5,
            width,
            height,
        )

    def _draw_grid(self, renderer, state: EditorViewportState) -> None:
        cx, cy = self.calculate_position()
        width, height = self.size
        half_w = width * 0.5
        half_h = height * 0.5

        # Adaptive grid keeps line density useful while zooming out.
        step_world = max(1.0, float(self.grid_size))
        while step_world * state.zoom < 18.0:
            step_world *= 2.0
        while step_world * state.zoom > 110.0 and step_world > 1.0:
            step_world *= 0.5

        left_world, top_world = state.screen_to_world(
            cx - half_w,
            cy - half_h,
            cx,
            cy,
        )
        right_world, bottom_world = state.screen_to_world(
            cx + half_w,
            cy + half_h,
            cx,
            cy,
        )

        grid_color = (0.13, 0.14, 0.16, 0.85)
        major_color = (0.18, 0.19, 0.22, 0.95)
        axis_x = (0.55, 0.20, 0.20, 0.95)
        axis_y = (0.20, 0.50, 0.25, 0.95)

        start_x = int(left_world // step_world) - 1
        end_x = int(right_world // step_world) + 1
        for cell in range(start_x, end_x + 1):
            wx = cell * step_world
            sx, _ = state.world_to_screen(wx, 0.0, cx, cy)
            color = major_color if cell % 4 == 0 else grid_color
            renderer.line(
                sx,
                cy - half_h,
                sx,
                cy + half_h,
                width=1.0,
                color=color,
                layer=-10000,
            )

        start_y = int(top_world // step_world) - 1
        end_y = int(bottom_world // step_world) + 1
        for cell in range(start_y, end_y + 1):
            wy = cell * step_world
            _, sy = state.world_to_screen(0.0, wy, cx, cy)
            color = major_color if cell % 4 == 0 else grid_color
            renderer.line(
                cx - half_w,
                sy,
                cx + half_w,
                sy,
                width=1.0,
                color=color,
                layer=-10000,
            )

        origin_x, origin_y = state.world_to_screen(0.0, 0.0, cx, cy)
        renderer.line(
            cx - half_w,
            origin_y,
            cx + half_w,
            origin_y,
            width=1.5,
            color=axis_x,
            layer=-9999,
        )
        renderer.line(
            origin_x,
            cy - half_h,
            origin_x,
            cy + half_h,
            width=1.5,
            color=axis_y,
            layer=-9999,
        )

    def _draw_selection(self, renderer, state: EditorViewportState) -> None:
        editor = self.editor_scene
        if editor is None:
            return
        node = editor.selection.selected
        if node is None or node is editor.document.scene.ui:
            return

        try:
            world_x, world_y = node.world_position
        except Exception:
            return

        cx, cy = self.calculate_position()
        sx, sy = state.world_to_screen(world_x, world_y, cx, cy)

        width = getattr(node, "width", 0.0)
        height = getattr(node, "height", 0.0)
        try:
            scale_x, scale_y = node.world_scale
        except Exception:
            scale_x = scale_y = 1.0

        try:
            width = abs(float(width) * float(scale_x) * state.zoom)
            height = abs(float(height) * float(scale_y) * state.zoom)
        except (TypeError, ValueError):
            width = height = 0.0

        width = max(18.0, width)
        height = max(18.0, height)
        left = sx - width * 0.5
        right = sx + width * 0.5
        top = sy - height * 0.5
        bottom = sy + height * 0.5
        color = (0.30, 0.62, 1.0, 1.0)

        renderer.line(left, top, right, top, width=2.0, color=color, layer=100000)
        renderer.line(right, top, right, bottom, width=2.0, color=color, layer=100000)
        renderer.line(right, bottom, left, bottom, width=2.0, color=color, layer=100000)
        renderer.line(left, bottom, left, top, width=2.0, color=color, layer=100000)
        renderer.circle(
            sx,
            sy,
            7.0,
            color=(0.30, 0.62, 1.0, 0.95),
            layer=100001,
        )

    def _draw_transform_gizmo(
        self,
        renderer,
        state: EditorViewportState,
    ) -> None:
        editor = self.editor_scene

        if editor is None:
            return

        if getattr(editor, "tilemap_tool", "select") != "select":
            return

        node = editor.selection.selected

        if (
            node is None
            or node is editor.document.scene.root
            or node is editor.document.scene.ui
        ):
            return

        try:
            world_x, world_y = (
                node.world_position
            )

        except Exception:
            return

        cx, cy = (
            self.calculate_position()
        )

        pivot_x, pivot_y = (
            state.world_to_screen(
                world_x,
                world_y,
                cx,
                cy,
            )
        )

        mode = getattr(
            editor,
            "viewport_tool",
            GIZMO_MOVE,
        )

        active_handle = getattr(
            editor,
            "_gizmo_active_handle",
            None,
        )

        x_color = (
            1.0,
            0.28,
            0.24,
            1.0,
        )

        y_color = (
            0.30,
            0.85,
            0.38,
            1.0,
        )

        center_color = (
            0.30,
            0.62,
            1.0,
            1.0,
        )

        highlight = (
            1.0,
            0.85,
            0.20,
            1.0,
        )

        layer = 100100

        if mode == GIZMO_ROTATE:
            color = (
                highlight
                if active_handle == "rotate"
                else (
                    0.42,
                    0.68,
                    1.0,
                    1.0,
                )
            )

            # Renderer circle takes diameter.
            renderer.circle(
                pivot_x,
                pivot_y,
                _GIZMO_ROTATE_RADIUS * 2.0,
                color=color,
                layer=layer,
            )

            renderer.circle(
                pivot_x,
                pivot_y,
                7.0,
                color=center_color,
                layer=layer + 1,
            )

            return

        x_draw = (
            highlight
            if active_handle == "x"
            else x_color
        )

        y_draw = (
            highlight
            if active_handle == "y"
            else y_color
        )

        center_draw = (
            highlight
            if active_handle in {
                "xy",
                "uniform",
            }
            else center_color
        )

        renderer.line(
            pivot_x,
            pivot_y,
            pivot_x + _GIZMO_AXIS_LENGTH,
            pivot_y,
            width=3.0,
            color=x_draw,
            layer=layer,
        )

        renderer.line(
            pivot_x,
            pivot_y,
            pivot_x,
            pivot_y + _GIZMO_AXIS_LENGTH,
            width=3.0,
            color=y_draw,
            layer=layer,
        )

        if mode == GIZMO_SCALE:
            renderer.rect(
                pivot_x + _GIZMO_AXIS_LENGTH,
                pivot_y,
                10.0,
                10.0,
                color=x_draw,
                layer=layer + 1,
            )

            renderer.rect(
                pivot_x,
                pivot_y + _GIZMO_AXIS_LENGTH,
                10.0,
                10.0,
                color=y_draw,
                layer=layer + 1,
            )

            renderer.rect(
                pivot_x,
                pivot_y,
                12.0,
                12.0,
                color=center_draw,
                layer=layer + 2,
            )

        else:
            # Simple arrow-like ends.
            renderer.triangle(
                pivot_x + _GIZMO_AXIS_LENGTH,
                pivot_y,
                pivot_x + _GIZMO_AXIS_LENGTH - 12.0,
                pivot_y - 6.0,
                pivot_x + _GIZMO_AXIS_LENGTH - 12.0,
                pivot_y + 6.0,
                color=x_draw,
                layer=layer + 1,
            )

            renderer.triangle(
                pivot_x,
                pivot_y + _GIZMO_AXIS_LENGTH,
                pivot_x - 6.0,
                pivot_y + _GIZMO_AXIS_LENGTH - 12.0,
                pivot_x + 6.0,
                pivot_y + _GIZMO_AXIS_LENGTH - 12.0,
                color=y_draw,
                layer=layer + 1,
            )

            renderer.rect(
                pivot_x,
                pivot_y,
                12.0,
                12.0,
                color=center_draw,
                layer=layer + 2,
            )

    def render(self, renderer) -> None:
        if not self.visible:
            return

        editor = self.editor_scene
        if editor is None:
            return

        cx, cy = self.calculate_position()
        width, height = self.size
        if width <= 1.0 or height <= 1.0:
            return

        clip_x, clip_y, clip_w, clip_h = self._clip_rect(renderer)
        renderer.push_clip_rect(
            clip_x,
            clip_y,
            clip_w,
            clip_h,
        )

        try:
            renderer.rect(
                cx,
                cy,
                width,
                height,
                color=self.background,
                layer=-11000,
            )

            state = editor.viewport_state
            if self.grid_enabled:
                self._draw_grid(renderer, state)

            proxy = EditorViewportRenderer(
                renderer,
                state,
                center_x=cx,
                center_y=cy,
                viewport_width=width,
                viewport_height=height,
            )

            # Editor documents are intentionally not active game scenes.
            # Render only their node tree; do not run gameplay updates or ECS
            # render systems that may own a frame-global renderer reference.
            editor.document.scene.root.render_tree(
                proxy,
                1.0,
            )

            self._draw_tilemap_hover(renderer, state)

            self._draw_selection(renderer, state)
            self._draw_transform_gizmo(
                renderer,
                state,
            )
        finally:
            renderer.pop_clip_rect()

        super().render(renderer)

    def _draw_tilemap_hover(
        self,
        renderer,
        state: EditorViewportState,
    ) -> None:
        editor = self.editor_scene
        if editor is None:
            return

        get_model = getattr(editor, "_selected_tilemap_editor_model", None)
        if not callable(get_model):
            return
        model = get_model()
        cell = getattr(editor, "_tilemap_hover_cell", None)
        if model is None or cell is None:
            return

        x, y = cell
        try:
            center_x, center_y = model.node.tile_world_position(x, y)
            tilemap = model.tilemap
        except (IndexError, RuntimeError, ValueError):
            return

        half_w = tilemap.tile_width * 0.5
        half_h = tilemap.tile_height * 0.5
        if tilemap.projection is TileProjection.ISOMETRIC:
            points = (
                (center_x, center_y - half_h),
                (center_x + half_w, center_y),
                (center_x, center_y + half_h),
                (center_x - half_w, center_y),
            )
        else:
            points = (
                (center_x - half_w, center_y - half_h),
                (center_x + half_w, center_y - half_h),
                (center_x + half_w, center_y + half_h),
                (center_x - half_w, center_y + half_h),
            )

        viewport_center = self.calculate_position()
        screen_points = [
            state.world_to_screen(px, py, *viewport_center)
            for px, py in points
        ]
        color = (0.95, 0.72, 0.18, 1.0)
        for index, (x1, y1) in enumerate(screen_points):
            x2, y2 = screen_points[(index + 1) % len(screen_points)]
            renderer.line(
                x1,
                y1,
                x2,
                y2,
                width=2.0,
                color=color,
                layer=100050,
            )
