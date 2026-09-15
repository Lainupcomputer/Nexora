from __future__ import annotations

from pathlib import Path

from nexora.rendering.camera import Camera
from nexora.rendering.gpu.render_snapshot import RenderSnapshot
from nexora.rendering.gpu.sprite_batch import GPUSpriteBatch
from nexora.rendering.gpu.rect_batch import GPURectBatch
from nexora.rendering.gpu.line_batch import GPULineBatch
from nexora.rendering.gpu.shape_batch import GPUShapeBatch
from nexora.rendering.gpu.text_renderer import GPUTextRenderer

from nexora.rendering.postprocessing.post_process import (
    PostProcess,
)


class GPURenderer:
    """
    High-level GPU renderer for Nexora.

    GPUContext owns:
        - SDL window
        - GPU device
        - swapchain
        - command buffer

    GPURenderer owns:
        - sprite batch
        - rectangle batch
        - line batch
        - shape batch
        - text renderer
        - post processor
        - render API
        - frame rendering
        - camera reference

    The sprite renderer supports multiple textures per frame.

    Submission order is preserved. Consecutive sprites using
    the same texture and clip rectangle are grouped into draw
    runs by GPUSpriteBatch.

    Public drawing API:
        - sprite()
        - sprites()
        - rect()
        - pixel()
        - line()
        - circle()
        - ellipse()
        - triangle()
        - polygon()
        - text()

    Render flow:

        begin_frame()

            submit draw commands

        end_frame()

            CPU instance data
                ↓
            GPU upload
                ↓
            render pass
                ↓
            swapchain

    With post-processing:

        Scene
          ↓
        Offscreen Render Target
          ↓
        PostProcess
          ↓
        Swapchain
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

        if not self.shader_dir.is_dir():
            raise FileNotFoundError(
                "Shader directory does not exist: "
                f"{self.shader_dir}"
            )

        # ======================================================
        # Camera
        # ======================================================

        self.camera = (
            camera
            if camera is not None
            else Camera()
        )

        # ======================================================
        # Limits
        # ======================================================

        if max_shapes is None:
            max_shapes = max_sprites

        if max_lines is None:
            max_lines = max_sprites

        # ======================================================
        # Sprites
        # ======================================================

        self.sprite_batch = GPUSpriteBatch(
            context,
            max_sprites=max_sprites,
            vertex_shader_path=(
                self.shader_dir
                / "sprite.vert.spv"
            ),
            fragment_shader_path=(
                self.shader_dir
                / "sprite.frag.spv"
            ),
            camera=self.camera,
            workers=workers,
        )

        # ======================================================
        # Rectangles
        # ======================================================

        self.rect_batch = GPURectBatch(
            context,
            max_rects=max_sprites,
            vertex_shader_path=(
                self.shader_dir
                / "rect.vert.spv"
            ),
            fragment_shader_path=(
                self.shader_dir
                / "rect.frag.spv"
            ),
            camera=self.camera,
        )

        # ======================================================
        # Lines
        # ======================================================

        self.line_batch = GPULineBatch(
            context,
            max_lines=max_lines,
            vertex_shader_path=(
                self.shader_dir
                / "line.vert.spv"
            ),
            fragment_shader_path=(
                self.shader_dir
                / "line.frag.spv"
            ),
            camera=self.camera,
        )

        # ======================================================
        # Shapes
        # ======================================================

        self.shape_batch = GPUShapeBatch(
            context,
            max_shapes=max_shapes,
            vertex_shader_path=(
                self.shader_dir
                / "shape.vert.spv"
            ),
            fragment_shader_path=(
                self.shader_dir
                / "shape.frag.spv"
            ),
            geometry_vertex_shader_path=(
                self.shader_dir
                / "geometry.vert.spv"
            ),
            geometry_fragment_shader_path=(
                self.shader_dir
                / "geometry.frag.spv"
            ),
            camera=self.camera,
        )

        # ======================================================
        # Text
        # ======================================================

        self.text_renderer = None

        if font is not None:
            self.text_renderer = GPUTextRenderer(
                context,
                font,
                vertex_shader_path=(
                    self.shader_dir
                    / "text.vert.spv"
                ),
                fragment_shader_path=(
                    self.shader_dir
                    / "text.frag.spv"
                ),
            )

        # ======================================================
        # Post processing
        # ======================================================

        self.post_processor = PostProcess(
            context,
            shader_dir=self.shader_dir,
        )

        # ======================================================
        # Frame state
        # ======================================================

        self._frame_started = False

        # ======================================================
        # Ordered render commands
        # ======================================================
        #
        # Commands currently cover sprites and rectangles/pixels.
        #
        # Tuple layout:
        #
        #   (
        #       layer,
        #       submission_index,
        #       kind,
        #       start,
        #       count,
        #   )
        #
        # Lower layers are drawn first. Commands on the same layer
        # preserve exact submission order.
        # ======================================================

        self._render_commands: list[
            tuple[
                int,
                int,
                str,
                int,
                int,
            ]
        ] = []

        self._submission_index = 0

        # ======================================================
        # Clipping
        # ======================================================

        self._clip_stack: list[
            tuple[
                float,
                float,
                float,
                float,
            ]
        ] = []

        # ======================================================
        # State
        # ======================================================

        self._destroyed = False

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def width(
        self,
    ) -> int:
        return (
            self.context.swapchain_width
            or self.context.width
        )

    @property
    def height(
        self,
    ) -> int:
        return (
            self.context.swapchain_height
            or self.context.height
        )

    @property
    def driver(
        self,
    ) -> str:
        return self.context.driver

    @property
    def post_processing(
        self,
    ) -> PostProcess:
        return self.post_processor

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

        Rectangles use:

            (x, y, width, height)
        """

        if not self._clip_stack:
            return None

        return self._clip_stack[-1]

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
        Push a clip rectangle.

        Nested clipping automatically creates the intersection
        between the current clip rectangle and the new one.
        """

        x = float(x)
        y = float(y)

        width = max(
            float(width),
            0.0,
        )

        height = max(
            float(height),
            0.0,
        )

        new_rect = (
            x,
            y,
            width,
            height,
        )

        current = self.clip_rect

        if current is not None:
            new_rect = (
                self._intersect_clip_rects(
                    current,
                    new_rect,
                )
            )

        self._clip_stack.append(
            new_rect
        )

        return new_rect

    def pop_clip_rect(
        self,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ] | None:
        if not self._clip_stack:
            raise RuntimeError(
                "Cannot pop clip rectangle: "
                "clip stack is empty"
            )

        self._clip_stack.pop()

        return self.clip_rect

    def clear_clip_rects(
        self,
    ) -> None:
        self._clip_stack.clear()

    @staticmethod
    def _intersect_clip_rects(
        a: tuple[
            float,
            float,
            float,
            float,
        ],
        b: tuple[
            float,
            float,
            float,
            float,
        ],
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b

        left = max(
            ax,
            bx,
        )

        top = max(
            ay,
            by,
        )

        right = min(
            ax + aw,
            bx + bw,
        )

        bottom = min(
            ay + ah,
            by + bh,
        )

        width = max(
            right - left,
            0.0,
        )

        height = max(
            bottom - top,
            0.0,
        )

        return (
            left,
            top,
            width,
            height,
        )

    # ==========================================================
    # Begin frame
    # ==========================================================

    def begin_frame(
        self,
    ) -> bool:
        if self._destroyed:
            raise RuntimeError(
                "GPURenderer has been destroyed"
            )

        if self._frame_started:
            raise RuntimeError(
                "GPU renderer frame already active"
            )

        # ------------------------------------------------------
        # Begin GPU frame
        # ------------------------------------------------------

        if not self.context.begin_frame():
            return False

        self._frame_started = True

        self._clip_stack.clear()

        self._render_commands.clear()
        self._submission_index = 0

        # ------------------------------------------------------
        # Begin batches
        # ------------------------------------------------------

        self.sprite_batch.begin()

        self.rect_batch.begin()

        self.line_batch.begin()

        self.shape_batch.begin()

        if self.text_renderer is not None:
            self.text_renderer.clear()

        return True

    # ==========================================================
    # End frame
    # ==========================================================

    def end_frame(
        self,
    ) -> bool:
        if self._destroyed:
            raise RuntimeError(
                "GPURenderer has been destroyed"
            )

        if not self._frame_started:
            raise RuntimeError(
                "GPU renderer frame is not active"
            )

        try:
            command_buffer = (
                self.context.command_buffer
            )

            # ==================================================
            # Upload GPU data
            # ==================================================

            self.sprite_batch.render_into(
                command_buffer
            )

            self.rect_batch.render_into(
                command_buffer
            )

            self.line_batch.render_into(
                command_buffer
            )

            self.shape_batch.render_into(
                command_buffer
            )

            if self.text_renderer is not None:
                self.text_renderer.render_into(
                    command_buffer
                )

            # ==================================================
            # Render
            # ==================================================

            if self.post_processor.enabled:
                self._render_with_post_processing(
                    command_buffer
                )

            else:
                self._render_direct()

            # ==================================================
            # Submit GPU frame
            # ==================================================

            self.context.end_frame()

            return True

        except Exception:
            # --------------------------------------------------
            # Only cancel if the context still owns an active
            # frame.
            # --------------------------------------------------

            if self.context.frame_active:
                try:
                    self.context.cancel_frame()

                except Exception:
                    pass

            raise

        finally:
            self._cleanup_frame()

    # ==========================================================
    # Direct rendering
    # ==========================================================

    def _render_direct(
        self,
    ) -> None:
        """
        Render the complete scene directly into the swapchain.
        """

        render_pass = (
            self.context.begin_render_pass(
                (
                    0.05,
                    0.05,
                    0.08,
                    1.0,
                )
            )
        )

        try:
            self._draw_scene(
                render_pass
            )

        finally:
            self.context.end_render_pass(
                render_pass
            )

    # ==========================================================
    # Post-processing rendering
    # ==========================================================

    def _render_with_post_processing(
        self,
        command_buffer,
    ) -> None:
        """
        Render scene into an offscreen target and then process
        that target into the swapchain.
        """

        # ------------------------------------------------------
        # Ensure render target matches viewport
        # ------------------------------------------------------

        self.post_processor.ensure_target(
            self.width,
            self.height,
        )

        scene_target = (
            self.post_processor.render_target
        )

        if scene_target is None:
            raise RuntimeError(
                "Post-processing render target "
                "could not be created"
            )

        # ======================================================
        # Pass 1
        #
        # Scene -> offscreen target
        # ======================================================

        scene_pass = (
            self.context.begin_render_pass(
                (
                    0.05,
                    0.05,
                    0.08,
                    1.0,
                ),
                target_texture=(
                    scene_target.texture
                ),
            )
        )

        try:
            self._draw_scene(
                scene_pass
            )

        finally:
            self.context.end_render_pass(
                scene_pass
            )

        # ======================================================
        # Pass 2
        #
        # Offscreen target -> post process -> swapchain
        # ======================================================

        post_pass = (
            self.context.begin_render_pass(
                (
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                )
            )
        )

        try:
            self.post_processor.draw(
                post_pass,
                command_buffer,
            )

        finally:
            self.context.end_render_pass(
                post_pass
            )


    # ==========================================================
    # Ordered command queue
    # ==========================================================

    def _queue_render_command(
        self,
        kind: str,
        start: int,
        count: int,
        layer: int,
    ) -> None:
        count = int(count)

        if count <= 0:
            return

        self._render_commands.append(
            (
                int(layer),
                self._submission_index,
                str(kind),
                int(start),
                count,
            )
        )

        self._submission_index += 1

    # ==========================================================
    # Draw scene
    # ==========================================================

    def _draw_scene(
        self,
        render_pass,
    ) -> None:
        """
        Draw all ordered render commands.

        Sorting rule:

            1. layer ascending
            2. original submission order
        """

        for (
            _layer,
            _submission_index,
            kind,
            start,
            count,
        ) in sorted(
            self._render_commands,
            key=lambda command: (
                command[0],
                command[1],
            ),
        ):
            if kind == "sprite":
                self.sprite_batch.draw_range(
                    render_pass,
                    start,
                    count,
                )

            elif kind == "rect":
                self.rect_batch.draw_range(
                    render_pass,
                    start,
                    count,
                )

            elif kind == "line":
                self.line_batch.draw_range(
                    render_pass,
                    start,
                    count,
                )

            elif kind == "shape":
                self.shape_batch.draw_shape_range(
                    render_pass,
                    start,
                    count,
                )

            elif kind == "geometry":
                self.shape_batch.draw_geometry_range(
                    render_pass,
                    start,
                    count,
                )

            elif kind == "text":
                if self.text_renderer is None:
                    raise RuntimeError(
                        "Text command queued but "
                        "text_renderer is None"
                    )

                self.text_renderer.draw_range(
                    render_pass,
                    start,
                    count,
                )

            else:
                raise RuntimeError(
                    "Unknown render command kind: "
                    f"{kind!r}"
                )

    # ==========================================================
    # Frame cleanup
    # ==========================================================

    def _cleanup_frame(
        self,
    ) -> None:
        """
        Reset all transient frame state.

        No private GPUSpriteBatch internals are touched here.
        """

        # ------------------------------------------------------
        # Clipping
        # ------------------------------------------------------

        self._clip_stack.clear()

        self._render_commands.clear()
        self._submission_index = 0

        # ------------------------------------------------------
        # Sprite batch
        # ------------------------------------------------------

        self.sprite_batch.clear()

        # ------------------------------------------------------
        # Other batches
        # ------------------------------------------------------

        self.rect_batch.clear()

        self.line_batch.clear()

        self.shape_batch.clear()

        # ------------------------------------------------------
        # Text
        # ------------------------------------------------------

        if self.text_renderer is not None:
            self.text_renderer.clear()

        # ------------------------------------------------------
        # Frame state
        # ------------------------------------------------------

        self._frame_started = False

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
        """
        Submit one sprite.

        Lower layers are drawn first. Sprites on the same layer
        preserve submission order.
        """

        self._require_frame()

        if texture is None:
            return

        start = self.sprite_batch.sprite_count

        self.sprite_batch.add(
            x,
            y,
            width,
            height,
            texture=texture,
            rotation=rotation,
            origin=origin,
            alpha=alpha,
            flip_x=flip_x,
            flip_y=flip_y,
            uv=uv,
            clip_rect=self.clip_rect,
        )

        self._queue_render_command(
            "sprite",
            start,
            1,
            layer,
        )

    # ==========================================================
    # Multiple sprites
    # ==========================================================

    def sprites(
        self,
        texture,
        sprites,
        *,
        workers: int | None = None,
        layer: int = 0,
    ) -> int:
        """
        Submit multiple sprites using the same texture.

        Different calls to sprites() may use different textures
        within the same frame.

        Expected sprite format:

            (
                x,
                y,
                width,
                height,
                rotation,
                origin_x,
                origin_y,
                alpha,
                flip_x,
                flip_y,
                uv_x,
                uv_y,
                uv_width,
                uv_height,
            )
        """

        self._require_frame()

        if texture is None:
            return 0

        if not hasattr(
            sprites,
            "__len__",
        ):
            sprites = list(
                sprites
            )

        if not sprites:
            return 0

        start = self.sprite_batch.sprite_count

        count = self.sprite_batch.add_many(
            sprites,
            texture=texture,
            workers=workers,
            clip_rect=self.clip_rect,
        )

        self._queue_render_command(
            "sprite",
            start,
            count,
            layer,
        )

        return count

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
        self._require_frame()

        start = self.rect_batch.rect_count

        self.rect_batch.add(
            x,
            y,
            width,
            height,
            color=color,
            rotation=rotation,
            origin=origin,
            radius=radius,
            clip_rect=self.clip_rect,
        )

        self._queue_render_command(
            "rect",
            start,
            1,
            layer,
        )

    # ==========================================================
    # Pixels
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
        self._require_frame()

        start = self.rect_batch.rect_count

        self.rect_batch.add(
            x,
            y,
            size,
            size,
            color=color,
            rotation=0.0,
            origin=(
                0.5,
                0.5,
            ),
            clip_rect=self.clip_rect,
        )

        self._queue_render_command(
            "rect",
            start,
            1,
            layer,
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
        self._require_frame()

        start = self.line_batch.line_count

        self.line_batch.add(
            x1,
            y1,
            x2,
            y2,
            width=width,
            color=color,
        )

        self._queue_render_command(
            "line",
            start,
            1,
            layer,
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
        self._require_frame()

        start = self.shape_batch.shape_count

        self.shape_batch.circle(
            x,
            y,
            diameter,
            color=color,
            rotation=rotation,
            origin=origin,
        )

        self._queue_render_command(
            "shape",
            start,
            1,
            layer,
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
        self._require_frame()

        start = self.shape_batch.shape_count

        self.shape_batch.ellipse(
            x,
            y,
            width,
            height,
            color=color,
            rotation=rotation,
            origin=origin,
        )

        self._queue_render_command(
            "shape",
            start,
            1,
            layer,
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
        self._require_frame()

        start = self.shape_batch.geometry_vertex_count

        self.shape_batch.triangle(
            x1,
            y1,
            x2,
            y2,
            x3,
            y3,
            color=color,
        )

        count = (
            self.shape_batch.geometry_vertex_count
            - start
        )

        self._queue_render_command(
            "geometry",
            start,
            count,
            layer,
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
        self._require_frame()

        points = list(points)
        start = self.shape_batch.geometry_vertex_count

        self.shape_batch.polygon(
            points,
            color=color,
        )

        count = (
            self.shape_batch.geometry_vertex_count
            - start
        )

        self._queue_render_command(
            "geometry",
            start,
            count,
            layer,
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
        """
        Draw text using GPUTextRenderer.

        The active renderer clip rectangle is automatically
        passed to GPUTextRenderer.
        """

        self._require_frame()

        if self.text_renderer is None:
            raise RuntimeError(
                "Text rendering is not initialized. "
                "Pass a font to GPURenderer(..., font=...)."
            )

        kwargs.setdefault(
            "clip_rect",
            self.clip_rect,
        )

        start = self.text_renderer.glyph_count

        count = self.text_renderer.draw(
            *args,
            **kwargs,
        )

        self._queue_render_command(
            "text",
            start,
            count,
            layer,
        )

        return count

    # ==========================================================
    # Text measurement
    # ==========================================================

    def text_measure(
        self,
        text: str,
        *,
        scale: float = 1.0,
    ) -> tuple[
        float,
        float,
    ]:
        if self.text_renderer is None:
            raise RuntimeError(
                "Text rendering is not initialized. "
                "Pass a font to GPURenderer(..., font=...)."
            )

        return self.text_renderer.measure(
            text,
            scale=scale,
        )

    # ==========================================================
    # Text baseline
    # ==========================================================

    def text_baseline(
        self,
        *,
        scale: float = 1.0,
    ) -> float:
        if self.text_renderer is None:
            raise RuntimeError(
                "Text rendering is not initialized. "
                "Pass a font to GPURenderer(..., font=...)."
            )

        if scale <= 0:
            raise ValueError(
                "scale must be greater than zero."
            )

        return (
            self.text_renderer.font.ascent
            * scale
        )

    # ==========================================================
    # ECS / RenderSnapshot
    # ==========================================================

    def submit(
        self,
        snapshot: RenderSnapshot,
        texture,
        *,
        layer: int = 0,
    ) -> int:
        """
        Submit a RenderSnapshot using the supplied texture.

        Snapshot sprites participate in the same global render
        layer queue as sprite(), rect(), line(), shapes and text.
        """

        self._require_frame()

        if texture is None:
            return 0

        start = self.sprite_batch.sprite_count

        count = self.sprite_batch.submit_snapshot(
            snapshot,
            texture=texture,
        )

        self._queue_render_command(
            "sprite",
            start,
            count,
            layer,
        )

        return count

    # ==========================================================
    # Validation
    # ==========================================================

    def _require_frame(
        self,
    ) -> None:
        if self._destroyed:
            raise RuntimeError(
                "GPURenderer has been destroyed"
            )

        if not self._frame_started:
            raise RuntimeError(
                "Call renderer.begin_frame() before drawing"
            )

    # ==========================================================
    # Resize
    # ==========================================================

    def resize(
        self,
        width: int,
        height: int,
    ) -> None:
        self.context.resize(
            width,
            height,
        )

    # ==========================================================
    # Shutdown
    # ==========================================================

    def destroy(
        self,
    ) -> None:
        if self._destroyed:
            return

        self._destroyed = True

        # ------------------------------------------------------
        # Wait for GPU before releasing resources
        # ------------------------------------------------------

        try:
            self.context.wait_idle()

        except Exception:
            pass

        # ------------------------------------------------------
        # Post processor
        # ------------------------------------------------------

        if self.post_processor is not None:
            try:
                self.post_processor.destroy()

            finally:
                self.post_processor = None

        # ------------------------------------------------------
        # Sprite batch
        # ------------------------------------------------------

        if self.sprite_batch is not None:
            try:
                self.sprite_batch.destroy()

            finally:
                self.sprite_batch = None

        # ------------------------------------------------------
        # Rectangle batch
        # ------------------------------------------------------

        if self.rect_batch is not None:
            try:
                self.rect_batch.destroy()

            finally:
                self.rect_batch = None

        # ------------------------------------------------------
        # Line batch
        # ------------------------------------------------------

        if self.line_batch is not None:
            try:
                self.line_batch.destroy()

            finally:
                self.line_batch = None

        # ------------------------------------------------------
        # Shape batch
        # ------------------------------------------------------

        if self.shape_batch is not None:
            try:
                self.shape_batch.destroy()

            finally:
                self.shape_batch = None

        # ------------------------------------------------------
        # Text renderer
        # ------------------------------------------------------

        if self.text_renderer is not None:
            try:
                self.text_renderer.destroy()

            finally:
                self.text_renderer = None

        # ------------------------------------------------------
        # State
        # ------------------------------------------------------

        self._clip_stack.clear()
        self._frame_started = False

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