from __future__ import annotations

from pathlib import Path

from nexora.rendering.camera import Camera
from nexora.rendering.gpu.renderer import GPURenderer
from nexora.lighting import LightingSystem


class Renderer:
    """
    Public Nexora renderer interface.

    Renderer wraps GPURenderer and exposes the high-level
    rendering API used by games, scenes and nodes.

    The underlying GPURenderer handles:

        - sprites
        - rectangles
        - lines
        - shapes
        - text
        - camera
        - post-processing
        - GPU frame submission

    Shader binaries are loaded from the shader directory
    supplied by the engine.
    """

    def __init__(
        self,
        context,
        *,
        shader_dir: str | Path,
        max_sprites: int = 10000,
        max_shapes: int | None = None,
        max_lines: int | None = None,
        workers: int = 4,
        camera: Camera | None = None,
        font=None,
    ) -> None:
        self.context = context

        # ======================================================
        # Shader directory
        # ======================================================

        self.shader_dir = Path(
            shader_dir
        ).expanduser().resolve()

        # ======================================================
        # GPU renderer
        # ======================================================

        self.gpu = GPURenderer(
            context,
            shader_dir=self.shader_dir,
            max_sprites=max_sprites,
            max_shapes=max_shapes,
            max_lines=max_lines,
            workers=workers,
            camera=camera,
            font=font,
        )

        # ======================================================
        # 2D lighting
        # ======================================================

        self.lighting = LightingSystem()

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def width(
        self,
    ) -> int:
        return self.gpu.width

    @property
    def height(
        self,
    ) -> int:
        return self.gpu.height

    @property
    def size(
        self,
    ) -> tuple[int, int]:
        return (
            self.width,
            self.height,
        )

    @property
    def driver(
        self,
    ) -> str:
        return self.gpu.driver

    # ==========================================================
    # Camera
    # ==========================================================

    @property
    def camera(
        self,
    ) -> Camera:
        return self.gpu.camera

    @camera.setter
    def camera(
        self,
        value: Camera,
    ) -> None:
        self.gpu.camera = value

        # ------------------------------------------------------
        # Keep GPU systems synchronized with the new camera.
        # ------------------------------------------------------

        self.gpu.sprite_batch.camera = value

        self.gpu.rect_batch.camera = value

        self.gpu.line_batch.camera = value

        self.gpu.shape_batch.camera = value

        if self.gpu.text_renderer is not None:
            if hasattr(
                self.gpu.text_renderer,
                "camera",
            ):
                self.gpu.text_renderer.camera = value

    # ==========================================================
    # Post processing
    # ==========================================================

    @property
    def post_processing(
        self,
    ):
        """
        Access the renderer post-processing system.

        Example:

            post = renderer.post_processing

            post.vignette = 0.5
            post.grayscale = 1.0

            post.brightness = 0.9
            post.contrast = 1.1
            post.saturation = 0.8
        """

        return self.gpu.post_processing

    @property
    def post_processor(
        self,
    ):
        """
        Alias for post_processing.
        """

        return self.gpu.post_processing

    # ==========================================================
    # Frame lifecycle
    # ==========================================================

    def begin_frame(
        self,
    ) -> bool:
        self.lighting.begin_frame()
        return self.gpu.begin_frame()

    def end_frame(
        self,
    ) -> bool:
        self.lighting.apply(
            self.gpu.post_processor,
            self.camera,
            self.width,
            self.height,
        )
        return self.gpu.end_frame()

    # ==========================================================
    # Render phases
    # ==========================================================

    @property
    def render_phase(self) -> str:
        return self.gpu.render_phase

    def set_render_phase(self, phase: str) -> None:
        self.gpu.set_render_phase(phase)

    def overlay_scope(self):
        return self.gpu.overlay_scope()

    def world_scope(self):
        return self.gpu.world_scope()

    # ==========================================================
    # Clipping
    # ==========================================================

    @property
    def clip_rect(
        self,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ] | None:
        """
        Return the currently active clip rectangle.

        The rectangle is represented as:

            (x, y, width, height)

        where x/y are the top-left corner.

        Returns None if no clip rectangle is active.
        """

        return self.gpu.clip_rect

    def push_clip_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        """
        Push a clip rectangle onto the renderer clip stack.

        Nested rectangles are intersected automatically with
        the currently active clip rectangle.
        """

        return self.gpu.push_clip_rect(
            x,
            y,
            width,
            height,
        )

    def pop_clip_rect(
        self,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ] | None:
        """
        Pop the most recently pushed clip rectangle.

        Returns the newly active clip rectangle or None.
        """

        return self.gpu.pop_clip_rect()

    def clear_clip_rects(
        self,
    ) -> None:
        """
        Clear all active clip rectangles.
        """

        self.gpu.clear_clip_rects()

    # ==========================================================
    # Sprites
    # ==========================================================

    def sprite(
        self,
        texture,
        x: float,
        y: float,
        *,
        width: float,
        height: float,
        rotation: float = 0.0,
        origin=(
            0.5,
            0.5,
        ),
        alpha: float = 1.0,
        flip_x: bool = False,
        flip_y: bool = False,
        uv=(
            0.0,
            0.0,
            1.0,
            1.0,
        ),
        layer: int = 0,
    ) -> None:
        self.gpu.sprite(
            texture,
            x,
            y,
            width=width,
            height=height,
            rotation=rotation,
            origin=origin,
            alpha=alpha,
            flip_x=flip_x,
            flip_y=flip_y,
            uv=uv,
            layer=layer,
        )

    def sprites(
        self,
        texture,
        sprites,
        *,
        workers: int | None = None,
        layer: int = 0,
    ) -> int:
        return self.gpu.sprites(
            texture,
            sprites,
            workers=workers,
            layer=layer,
        )

    # ==========================================================
    # Rectangles
    # ==========================================================

    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        color=(
            1.0,
            1.0,
            1.0,
            1.0,
        ),
        rotation: float = 0.0,
        origin=(
            0.5,
            0.5,
        ),
        radius: float = 0.0,
        layer: int = 0,
    ) -> None:
        self.gpu.rect(
            x,
            y,
            width,
            height,
            color=color,
            rotation=rotation,
            origin=origin,
            radius=radius,
            layer=layer,
        )

    # ==========================================================
    # Pixel
    # ==========================================================

    def pixel(
        self,
        x: float,
        y: float,
        *,
        color=(
            1.0,
            1.0,
            1.0,
            1.0,
        ),
        size: float = 1.0,
        layer: int = 0,
    ) -> None:
        self.gpu.pixel(
            x,
            y,
            color=color,
            size=size,
            layer=layer,
        )

    # ==========================================================
    # Lines
    # ==========================================================

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        width: float = 1.0,
        color=(
            1.0,
            1.0,
            1.0,
            1.0,
        ),
        layer: int = 0,
    ) -> None:
        self.gpu.line(
            x1,
            y1,
            x2,
            y2,
            width=width,
            color=color,
            layer=layer,
        )

    # ==========================================================
    # Circle
    # ==========================================================

    def circle(
        self,
        x: float,
        y: float,
        diameter: float,
        *,
        color=(
            1.0,
            1.0,
            1.0,
            1.0,
        ),
        rotation: float = 0.0,
        origin=(
            0.5,
            0.5,
        ),
        layer: int = 0,
    ) -> None:
        self.gpu.circle(
            x,
            y,
            diameter,
            color=color,
            rotation=rotation,
            origin=origin,
            layer=layer,
        )

    # ==========================================================
    # Ellipse
    # ==========================================================

    def ellipse(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        color=(
            1.0,
            1.0,
            1.0,
            1.0,
        ),
        rotation: float = 0.0,
        origin=(
            0.5,
            0.5,
        ),
        layer: int = 0,
    ) -> None:
        self.gpu.ellipse(
            x,
            y,
            width,
            height,
            color=color,
            rotation=rotation,
            origin=origin,
            layer=layer,
        )

    # ==========================================================
    # Triangle
    # ==========================================================

    def triangle(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        x3: float,
        y3: float,
        *,
        color=(
            1.0,
            1.0,
            1.0,
            1.0,
        ),
        layer: int = 0,
    ) -> None:
        self.gpu.triangle(
            x1,
            y1,
            x2,
            y2,
            x3,
            y3,
            color=color,
            layer=layer,
        )

    # ==========================================================
    # Polygon
    # ==========================================================

    def polygon(
        self,
        points,
        *,
        color=(
            1.0,
            1.0,
            1.0,
            1.0,
        ),
        layer: int = 0,
    ) -> None:
        self.gpu.polygon(
            points,
            color=color,
            layer=layer,
        )

    # ==========================================================
    # Text
    # ==========================================================

    def text(
        self,
        *args,
        layer: int = 0,
        **kwargs,
    ):
        return self.gpu.text(
            *args,
            layer=layer,
            **kwargs,
        )

    def text_measure(
        self,
        text: str,
        *,
        scale: float = 1.0,
    ) -> tuple[
        float,
        float,
    ]:
        return self.gpu.text_measure(
            text,
            scale=scale,
        )

    def text_baseline(
        self,
        *,
        scale: float = 1.0,
    ) -> float:
        return self.gpu.text_baseline(
            scale=scale,
        )

    # ==========================================================
    # Render snapshot
    # ==========================================================

    def submit(
        self,
        snapshot,
        texture,
        *,
        layer: int = 0,
    ) -> int:
        return self.gpu.submit(
            snapshot,
            texture,
            layer=layer,
        )

    # ==========================================================
    # Resize
    # ==========================================================

    def resize(
        self,
        width: int,
        height: int,
    ) -> None:
        self.gpu.resize(
            width,
            height,
        )

    # ==========================================================
    # Shutdown
    # ==========================================================

    def destroy(
        self,
    ) -> None:
        self.gpu.destroy()

    # ==========================================================
    # Context manager
    # ==========================================================

    def __enter__(
        self,
    ):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.destroy()