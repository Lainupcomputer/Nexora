from __future__ import annotations

from contextlib import nullcontext

from nexora.rendering.camera import Camera

from .state import EditorViewportState

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
