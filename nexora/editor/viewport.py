from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from math import atan2, cos, degrees, hypot, radians, sin

from nexora.nodes.ui.ui_node import UINode
from nexora.rendering.camera import Camera
from nexora.tilemap import TileProjection


@dataclass(slots=True)
class EditorViewportState:
    """Pan/zoom state for the editor's 2D viewport."""

    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0
    min_zoom: float = 0.10
    max_zoom: float = 8.0

    def clamp_zoom(self, value: float) -> float:
        return max(
            self.min_zoom,
            min(
                self.max_zoom,
                float(value),
            ),
        )

    def world_to_screen(
        self,
        world_x: float,
        world_y: float,
        center_x: float,
        center_y: float,
    ) -> tuple[float, float]:
        return (
            center_x + (float(world_x) - self.x) * self.zoom,
            center_y + (float(world_y) - self.y) * self.zoom,
        )

    def screen_to_world(
        self,
        screen_x: float,
        screen_y: float,
        center_x: float,
        center_y: float,
    ) -> tuple[float, float]:
        zoom = max(self.zoom, 1e-9)
        return (
            self.x + (float(screen_x) - center_x) / zoom,
            self.y + (float(screen_y) - center_y) / zoom,
        )

    def pan_screen_delta(
        self,
        dx: float,
        dy: float,
    ) -> None:
        zoom = max(self.zoom, 1e-9)
        self.x -= float(dx) / zoom
        self.y -= float(dy) / zoom

    def zoom_at(
        self,
        screen_x: float,
        screen_y: float,
        center_x: float,
        center_y: float,
        factor: float,
    ) -> None:
        before_x, before_y = self.screen_to_world(
            screen_x,
            screen_y,
            center_x,
            center_y,
        )

        self.zoom = self.clamp_zoom(
            self.zoom * float(factor)
        )

        self.x = (
            before_x
            - (screen_x - center_x) / self.zoom
        )
        self.y = (
            before_y
            - (screen_y - center_y) / self.zoom
        )

    def reset(self) -> None:
        self.x = 0.0
        self.y = 0.0
        self.zoom = 1.0



GIZMO_MOVE = "move"
GIZMO_ROTATE = "rotate"
GIZMO_SCALE = "scale"

_GIZMO_AXIS_LENGTH = 72.0
_GIZMO_HIT_RADIUS = 9.0
_GIZMO_ROTATE_RADIUS = 54.0


def _distance_to_segment(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:
    """Return the screen-space distance from a point to a line segment."""

    dx = x2 - x1
    dy = y2 - y1

    length_sq = dx * dx + dy * dy

    if length_sq <= 1e-12:
        return hypot(
            px - x1,
            py - y1,
        )

    t = (
        (px - x1) * dx
        + (py - y1) * dy
    ) / length_sq

    t = max(
        0.0,
        min(
            1.0,
            t,
        ),
    )

    nearest_x = x1 + dx * t
    nearest_y = y1 + dy * t

    return hypot(
        px - nearest_x,
        py - nearest_y,
    )


def gizmo_hit_test(
    mode: str,
    *,
    mouse_x: float,
    mouse_y: float,
    pivot_x: float,
    pivot_y: float,
) -> str | None:
    """Return the transform gizmo handle under the pointer."""

    mode = str(
        mode
    ).lower()

    if mode == GIZMO_ROTATE:
        distance = hypot(
            mouse_x - pivot_x,
            mouse_y - pivot_y,
        )

        if (
            abs(
                distance
                - _GIZMO_ROTATE_RADIUS
            )
            <= _GIZMO_HIT_RADIUS
        ):
            return "rotate"

        return None

    # Small center handle allows free move / uniform scale.
    if (
        abs(mouse_x - pivot_x) <= 8.0
        and abs(mouse_y - pivot_y) <= 8.0
    ):
        if mode == GIZMO_SCALE:
            return "uniform"

        return "xy"

    x_distance = _distance_to_segment(
        mouse_x,
        mouse_y,
        pivot_x + 10.0,
        pivot_y,
        pivot_x + _GIZMO_AXIS_LENGTH,
        pivot_y,
    )

    y_distance = _distance_to_segment(
        mouse_x,
        mouse_y,
        pivot_x,
        pivot_y + 10.0,
        pivot_x,
        pivot_y + _GIZMO_AXIS_LENGTH,
    )

    if (
        x_distance <= _GIZMO_HIT_RADIUS
        and x_distance <= y_distance
    ):
        return "x"

    if y_distance <= _GIZMO_HIT_RADIUS:
        return "y"

    return None


def world_delta_to_local(
    node,
    dx: float,
    dy: float,
) -> tuple[float, float]:
    """Convert a world-space movement delta into the node parent's space."""

    parent = getattr(
        node,
        "parent",
        None,
    )

    if parent is None:
        return float(dx), float(dy)

    try:
        rotation = radians(
            float(
                parent.world_rotation
            )
        )

        scale_x, scale_y = (
            parent.world_scale
        )

        scale_x = float(
            scale_x
        )
        scale_y = float(
            scale_y
        )

    except Exception:
        return float(dx), float(dy)

    # Inverse parent rotation.
    cos_angle = cos(
        rotation
    )
    sin_angle = sin(
        rotation
    )

    local_x = (
        float(dx) * cos_angle
        + float(dy) * sin_angle
    )

    local_y = (
        -float(dx) * sin_angle
        + float(dy) * cos_angle
    )

    if abs(scale_x) > 1e-9:
        local_x /= scale_x

    if abs(scale_y) > 1e-9:
        local_y /= scale_y

    return local_x, local_y


def drag_angle_degrees(
    mouse_x: float,
    mouse_y: float,
    pivot_x: float,
    pivot_y: float,
) -> float:
    """Angle of a pointer around a gizmo pivot in screen coordinates."""

    return degrees(
        atan2(
            mouse_y - pivot_y,
            mouse_x - pivot_x,
        )
    )


class _NullLighting:
    def submit(self, _snapshot) -> bool:
        return False


class EditorViewportRenderer:
    """Renderer proxy that maps world coordinates into an editor viewport.

    The normal Nexora renderer has one frame-wide camera uniform. The editor UI
    is rendered in screen space during the overlay phase, so temporarily
    changing the global renderer camera would also move the editor UI queued in
    the same frame. This proxy instead transforms primitive coordinates before
    they are submitted to the real renderer.
    """

    def __init__(
        self,
        renderer,
        state: EditorViewportState,
        *,
        center_x: float,
        center_y: float,
        viewport_width: float,
        viewport_height: float,
    ) -> None:
        self._renderer = renderer
        self._state = state
        self._center_x = float(center_x)
        self._center_y = float(center_y)
        self._width = max(1.0, float(viewport_width))
        self._height = max(1.0, float(viewport_height))

        # Editor UI panels also submit at the renderer's default layer 0.
        # Document nodes rendered through this proxy therefore need their own
        # positive layer range, otherwise a later UI panel/background command
        # can cover world sprites even though the sprite itself rendered
        # correctly.
        #
        # Selection/gizmos use ~100_000, so 50_000 keeps document content
        # above editor chrome and below editor overlays.
        self._layer_base = 50_000

        self._camera = Camera(
            x=state.x,
            y=state.y,
            zoom=state.zoom,
            target_zoom=state.zoom,
            min_zoom=state.min_zoom,
            max_zoom=state.max_zoom,
        )
        self.lighting = _NullLighting()

    @property
    def width(self) -> int:
        return int(self._width)

    @property
    def height(self) -> int:
        return int(self._height)

    @property
    def size(self) -> tuple[int, int]:
        return self.width, self.height

    @property
    def camera(self) -> Camera:
        return self._camera

    @property
    def clip_rect(self):
        return self._renderer.clip_rect

    def overlay_scope(self):
        return nullcontext()

    def world_scope(self):
        return nullcontext()

    def _point(
        self,
        x: float,
        y: float,
    ) -> tuple[float, float]:
        return self._state.world_to_screen(
            x,
            y,
            self._center_x,
            self._center_y,
        )

    def _scale(self, value: float) -> float:
        return float(value) * self._state.zoom

    def _layer(self, layer: int) -> int:
        return self._layer_base + int(layer)

    def sprite(
        self,
        texture,
        x: float,
        y: float,
        *,
        width: float,
        height: float,
        rotation: float = 0.0,
        origin=(0.5, 0.5),
        alpha: float = 1.0,
        flip_x: bool = False,
        flip_y: bool = False,
        uv=(0.0, 0.0, 1.0, 1.0),
        layer: int = 0,
    ) -> None:
        sx, sy = self._point(x, y)
        self._renderer.sprite(
            texture,
            sx,
            sy,
            width=self._scale(width),
            height=self._scale(height),
            rotation=rotation,
            origin=origin,
            alpha=alpha,
            flip_x=flip_x,
            flip_y=flip_y,
            uv=uv,
            layer=self._layer(layer),
        )

    def sprites(
        self,
        texture,
        sprites,
        *,
        workers: int | None = None,
        layer: int = 0,
    ) -> int:
        transformed = []
        for item in sprites:
            values = list(item)
            if len(values) < 4:
                continue
            values[0], values[1] = self._point(
                values[0],
                values[1],
            )
            values[2] = self._scale(values[2])
            values[3] = self._scale(values[3])
            transformed.append(tuple(values))
        return self._renderer.sprites(
            texture,
            transformed,
            workers=workers,
            layer=self._layer(layer),
        )

    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        color=(1.0, 1.0, 1.0, 1.0),
        rotation: float = 0.0,
        origin=(0.5, 0.5),
        radius: float = 0.0,
        layer: int = 0,
    ) -> None:
        sx, sy = self._point(x, y)
        self._renderer.rect(
            sx,
            sy,
            self._scale(width),
            self._scale(height),
            color=color,
            rotation=rotation,
            origin=origin,
            radius=self._scale(radius),
            layer=self._layer(layer),
        )

    def pixel(
        self,
        x: float,
        y: float,
        *,
        color=(1.0, 1.0, 1.0, 1.0),
        size: float = 1.0,
        layer: int = 0,
    ) -> None:
        sx, sy = self._point(x, y)
        self._renderer.pixel(
            sx,
            sy,
            color=color,
            size=self._scale(size),
            layer=self._layer(layer),
        )

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        width: float = 1.0,
        color=(1.0, 1.0, 1.0, 1.0),
        layer: int = 0,
    ) -> None:
        sx1, sy1 = self._point(x1, y1)
        sx2, sy2 = self._point(x2, y2)
        self._renderer.line(
            sx1,
            sy1,
            sx2,
            sy2,
            width=max(1.0, self._scale(width)),
            color=color,
            layer=self._layer(layer),
        )

    def circle(
        self,
        x: float,
        y: float,
        diameter: float,
        *,
        color=(1.0, 1.0, 1.0, 1.0),
        rotation: float = 0.0,
        origin=(0.5, 0.5),
        layer: int = 0,
    ) -> None:
        sx, sy = self._point(x, y)
        self._renderer.circle(
            sx,
            sy,
            self._scale(diameter),
            color=color,
            rotation=rotation,
            origin=origin,
            layer=self._layer(layer),
        )

    def ellipse(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        color=(1.0, 1.0, 1.0, 1.0),
        rotation: float = 0.0,
        origin=(0.5, 0.5),
        layer: int = 0,
    ) -> None:
        sx, sy = self._point(x, y)
        self._renderer.ellipse(
            sx,
            sy,
            self._scale(width),
            self._scale(height),
            color=color,
            rotation=rotation,
            origin=origin,
            layer=self._layer(layer),
        )

    def triangle(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        x3: float,
        y3: float,
        *,
        color=(1.0, 1.0, 1.0, 1.0),
        layer: int = 0,
    ) -> None:
        p1 = self._point(x1, y1)
        p2 = self._point(x2, y2)
        p3 = self._point(x3, y3)
        self._renderer.triangle(
            *p1,
            *p2,
            *p3,
            color=color,
            layer=self._layer(layer),
        )

    def polygon(
        self,
        points,
        *,
        color=(1.0, 1.0, 1.0, 1.0),
        layer: int = 0,
    ) -> None:
        self._renderer.polygon(
            [
                self._point(x, y)
                for x, y in points
            ],
            color=color,
            layer=self._layer(layer),
        )

    def text_measure(self, *args, **kwargs):
        return self._renderer.text_measure(*args, **kwargs)

    def text_baseline(self, *args, **kwargs):
        return self._renderer.text_baseline(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self._renderer, name)


class EditorViewportCanvas(UINode):
    """UI node responsible for rendering the editable scene preview."""

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)
        self.editor_scene = None
        self.grid_enabled = True
        self.grid_size = 32.0
        self.background = (0.055, 0.060, 0.070, 1.0)

    @staticmethod
    def _rgba255(color) -> tuple[float, float, float, float]:
        values = tuple(color)
        if not values:
            return (1.0, 1.0, 1.0, 1.0)
        if max(values) > 1.0:
            values = tuple(float(v) / 255.0 for v in values)
        if len(values) == 3:
            return (*values, 1.0)
        return tuple(values[:4])

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

        model = editor._selected_tilemap_editor_model()
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


def node_hit_distance(
    node,
    *,
    mouse_x: float,
    mouse_y: float,
    state: EditorViewportState,
    center_x: float,
    center_y: float,
) -> float | None:
    """Return screen-space hit distance for one node, or None."""

    if not getattr(node, "visible", True):
        return None

    try:
        world_x, world_y = node.world_position
    except Exception:
        return None

    sx, sy = state.world_to_screen(
        world_x,
        world_y,
        center_x,
        center_y,
    )

    width = getattr(node, "width", 0.0)
    height = getattr(node, "height", 0.0)
    try:
        scale_x, scale_y = node.world_scale
        width = abs(float(width) * float(scale_x) * state.zoom)
        height = abs(float(height) * float(scale_y) * state.zoom)
    except (TypeError, ValueError, AttributeError):
        width = height = 0.0

    half_w = max(9.0, width * 0.5)
    half_h = max(9.0, height * 0.5)

    if (
        sx - half_w <= mouse_x <= sx + half_w
        and sy - half_h <= mouse_y <= sy + half_h
    ):
        return hypot(mouse_x - sx, mouse_y - sy)

    return None
