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

    Shader binaries are loaded from the shader directory
    supplied by the engine.

    The current sprite batch supports one texture per frame.
    The sprite batch is initialized lazily when the first
    textured sprite is submitted.

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

    Render flow with post-processing enabled:

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

        # Texture currently assigned to SpriteBatch.
        #
        # None means that no sprite has been submitted during
        # the current frame yet.
        self._active_texture = None

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
        """
        Public access to the post-processing system.
        """

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

        Rectangles are represented as:

            (x, y, width, height)

        where x/y are the top-left corner.
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

        If another clip rectangle is active, the new rectangle
        is intersected with it.
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
            new_rect = self._intersect_clip_rects(
                current,
                new_rect,
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
        """
        Pop the most recently pushed clip rectangle.
        """

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
        """
        Clear the complete clip stack.
        """

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
        """
        Return the intersection of two clip rectangles.
        """

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
    # Frame
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

        if not self.context.begin_frame():
            return False

        self._frame_started = True

        self._active_texture = None

        self._clip_stack.clear()

        # ------------------------------------------------------
        # Begin batches
        # ------------------------------------------------------
        #
        # IMPORTANT:
        #
        # GPUSpriteBatch.begin() requires a texture.
        # At this point no sprite texture is known yet.
        #
        # Therefore the sprite batch is started lazily inside
        # _set_texture() when the first sprite is submitted.
        # ------------------------------------------------------

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
            # Prepare GPU data
            # ==================================================

            if self._active_texture is not None:
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
            # Submit frame
            # ==================================================

            self.context.end_frame()

            return True

        except Exception:
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
        Render directly into the swapchain.

        Used when post-processing is disabled.
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
    # Post processing rendering
    # ==========================================================

    def _render_with_post_processing(
        self,
        command_buffer,
    ) -> None:
        """
        Render the scene into an offscreen render target and
        then process it into the swapchain.
        """

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
        # Scene -> offscreen texture
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
        # Offscreen -> post process -> swapchain
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
    # Draw scene
    # ==========================================================

    def _draw_scene(
        self,
        render_pass,
    ) -> None:
        """
        Draw all currently submitted render batches.
        """

        # ------------------------------------------------------
        # Sprites
        # ------------------------------------------------------

        if self._active_texture is not None:
            self.sprite_batch.draw_into(
                render_pass
            )

        # ------------------------------------------------------
        # Rectangles
        # ------------------------------------------------------

        self.rect_batch.draw_into(
            render_pass
        )

        # ------------------------------------------------------
        # Lines
        # ------------------------------------------------------

        self.line_batch.draw_into(
            render_pass
        )

        # ------------------------------------------------------
        # Shapes
        # ------------------------------------------------------

        self.shape_batch.draw_into(
            render_pass
        )

        # ------------------------------------------------------
        # Text
        # ------------------------------------------------------

        if self.text_renderer is not None:
            self.text_renderer.draw_into(
                render_pass
            )

    # ==========================================================
    # ==========================================================
    # Frame cleanup
    # ==========================================================

    def _cleanup_frame(
        self,
    ) -> None:
        """
        Reset transient frame state after rendering.
        """

        # ------------------------------------------------------
        # Frame state
        # ------------------------------------------------------

        self._active_texture = None

        self._clip_stack.clear()

        self._frame_started = False

        # ------------------------------------------------------
        # Sprite batch
        # ------------------------------------------------------
        #
        # GPUSpriteBatch currently has no public clear() method.
        # Reset its transient per-frame state manually.
        # ------------------------------------------------------

        self.sprite_batch._texture = None
        self.sprite_batch._sprite_count = 0

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
    ) -> None:
        """
        Submit one sprite.
        """

        self._require_frame()

        if texture is None:
            return

        self._set_texture(
            texture
        )

        self.sprite_batch.add(
            x,
            y,
            width,
            height,
            rotation=rotation,
            origin=origin,
            alpha=alpha,
            flip_x=flip_x,
            flip_y=flip_y,
            uv=uv,
            clip_rect=self.clip_rect,
        )

    def sprites(
        self,
        texture,
        sprites,
        *,
        workers: int | None = None,
    ) -> int:
        """
        Submit many sprites using one texture.

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

        self._set_texture(
            texture
        )

        return self.sprite_batch.add_many(
            sprites,
            workers=workers,
            clip_rect=self.clip_rect,
        )

    # ==========================================================
    # Texture handling
    # ==========================================================

    def _set_texture(
        self,
        texture,
    ) -> None:
        """
        Initialize the sprite batch with the first texture used
        during the current frame.

        The current GPUSpriteBatch supports one texture per
        frame.
        """

        if texture is None:
            return

        if self._active_texture is texture:
            return

        if self._active_texture is not None:
            raise RuntimeError(
                "Multiple textures in one frame are not "
                "supported by the current GPUSpriteBatch."
            )

        self._active_texture = texture

        self.sprite_batch.begin(
            texture
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
    ) -> None:
        self._require_frame()

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
    ) -> None:
        self._require_frame()

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
    ) -> None:
        self._require_frame()

        self.line_batch.add(
            x1,
            y1,
            x2,
            y2,
            width=width,
            color=color,
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
    ) -> None:
        self._require_frame()

        self.shape_batch.circle(
            x,
            y,
            diameter,
            color=color,
            rotation=rotation,
            origin=origin,
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
    ) -> None:
        self._require_frame()

        self.shape_batch.ellipse(
            x,
            y,
            width,
            height,
            color=color,
            rotation=rotation,
            origin=origin,
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
    ) -> None:
        self._require_frame()

        self.shape_batch.triangle(
            x1,
            y1,
            x2,
            y2,
            x3,
            y3,
            color=color,
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
    ) -> None:
        self._require_frame()

        self.shape_batch.polygon(
            points,
            color=color,
        )

    # ==========================================================
    # Text
    # ==========================================================

    def text(
        self,
        *args,
        **kwargs,
    ):
        """
        Draw text using GPUTextRenderer.

        The currently active renderer clip rectangle is
        automatically attached to the text draw command.
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

        return self.text_renderer.draw(
            *args,
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
        if self.text_renderer is None:
            raise RuntimeError(
                "Text rendering is not initialized. "
                "Pass a font to GPURenderer(..., font=...)."
            )

        return self.text_renderer.measure(
            text,
            scale=scale,
        )

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
    # ECS / Snapshot
    # ==========================================================

    def submit(
        self,
        snapshot: RenderSnapshot,
        texture,
    ) -> int:
        """
        Submit a RenderSnapshot using one texture.
        """

        self._require_frame()

        if texture is None:
            return 0

        self._set_texture(
            texture
        )

        return self.sprite_batch.submit_snapshot(
            snapshot
        )

    # ==========================================================
    # Validation
    # ==========================================================

    def _require_frame(
        self,
    ) -> None:
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

        self._active_texture = None

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