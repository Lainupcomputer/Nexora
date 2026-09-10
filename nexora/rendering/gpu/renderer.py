from __future__ import annotations

from pathlib import Path

from nexora.rendering.camera import Camera
from nexora.rendering.gpu.render_snapshot import RenderSnapshot
from nexora.rendering.gpu.sprite_batch import GPUSpriteBatch


class GPURenderer:
    """
    High-level GPU renderer for Nexora.

    GPUContext owns:
        - SDL window
        - GPU device
        - swapchain
        - command buffer

    GPURenderer owns:
        - sprite batches
        - render API
        - frame rendering
        - camera reference
    """

    def __init__(
        self,
        context,
        *,
        max_sprites: int = 10000,
        workers: int = 4,
        camera: Camera | None = None,
    ) -> None:
        self.context = context

        # The GPURenderer keeps the exact same Camera object
        # that is exposed by the public Renderer.
        self.camera = camera if camera is not None else Camera()

        shader_dir = (
            Path(__file__).resolve().parent.parent
            / "shaders"
            / "bin"
        )

        self.sprite_batch = GPUSpriteBatch(
            context,
            max_sprites=max_sprites,
            vertex_shader_path=(
                shader_dir / "sprite.vert.spv"
            ),
            fragment_shader_path=(
                shader_dir / "sprite.frag.spv"
            ),
            camera=self.camera,
            workers=workers,
        )

        self._frame_started = False
        self._active_texture = None
        self._destroyed = False

    # ==========================================================
    # PROPERTIES
    # ==========================================================

    @property
    def width(self) -> int:
        return (
            self.context.swapchain_width
            or self.context.width
        )

    @property
    def height(self) -> int:
        return (
            self.context.swapchain_height
            or self.context.height
        )

    @property
    def driver(self) -> str:
        return self.context.driver

    # ==========================================================
    # FRAME
    # ==========================================================

    def begin_frame(self) -> bool:
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

        return True

    def end_frame(self) -> bool:
        if self._destroyed:
            raise RuntimeError(
                "GPURenderer has been destroyed"
            )

        if not self._frame_started:
            raise RuntimeError(
                "GPU renderer frame is not active"
            )

        try:
            if self._active_texture is None:
                render_pass = self.context.begin_render_pass(
                    (
                        0.05,
                        0.05,
                        0.08,
                        1.0,
                    )
                )

                try:
                    pass
                finally:
                    self.context.end_render_pass(
                        render_pass
                    )

            else:
                command_buffer = (
                    self.context.command_buffer
                )

                self.sprite_batch.render_into(
                    command_buffer
                )

                render_pass = self.context.begin_render_pass(
                    (
                        0.05,
                        0.05,
                        0.08,
                        1.0,
                    )
                )

                try:
                    self.sprite_batch.draw_into(
                        render_pass
                    )
                finally:
                    self.context.end_render_pass(
                        render_pass
                    )

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
            self._active_texture = None
            self._frame_started = False

            self.sprite_batch._texture = None
            self.sprite_batch._sprite_count = 0

    # ==========================================================
    # SPRITES
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
        origin=(0.5, 0.5),
        alpha: float = 1.0,
        flip_x: bool = False,
        flip_y: bool = False,
        uv=(0.0, 0.0, 1.0, 1.0),
    ) -> None:
        self._require_frame()

        self._set_texture(texture)

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
        )

    def sprites(
        self,
        texture,
        sprites,
        *,
        workers: int | None = None,
    ) -> int:
        self._require_frame()

        self._set_texture(texture)

        return self.sprite_batch.add_many(
            sprites,
            workers=workers,
        )

    # ==========================================================
    # ECS / SNAPSHOT
    # ==========================================================

    def submit(
        self,
        snapshot: RenderSnapshot,
        texture,
    ) -> int:
        self._require_frame()

        self._set_texture(texture)

        return self.sprite_batch.submit_snapshot(
            snapshot
        )

    # ==========================================================
    # TEXTURE
    # ==========================================================

    def _set_texture(self, texture) -> None:
        if self._active_texture is texture:
            return

        if self._active_texture is not None:
            raise RuntimeError(
                "Multiple textures in one frame are not "
                "supported by the current SpriteBatch. "
                "Texture batching will be added next."
            )

        self._active_texture = texture

        self.sprite_batch.begin(
            texture
        )

    # ==========================================================
    # VALIDATION
    # ==========================================================

    def _require_frame(self) -> None:
        if not self._frame_started:
            raise RuntimeError(
                "Call renderer.begin_frame() before drawing"
            )

    # ==========================================================
    # RESIZE
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
    # SHUTDOWN
    # ==========================================================

    def destroy(self) -> None:
        if self._destroyed:
            return

        self._destroyed = True

        try:
            self.sprite_batch.destroy()
        finally:
            self._active_texture = None

    # ==========================================================
    # CONTEXT MANAGER
    # ==========================================================

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.destroy()

