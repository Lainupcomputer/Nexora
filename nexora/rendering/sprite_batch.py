
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from nexora.rendering.gpu.sprite_batch import GPUSpriteBatch
from nexora.threading.context import ThreadContext


@dataclass(slots=True)
class BatchSprite:
    """
    Description of one GPU sprite.
    """

    texture: object
    x: float
    y: float

    width: float | None = None
    height: float | None = None

    rotation: float = 0.0
    scale: float = 1.0

    origin: tuple[float, float] = (
        0.5,
        0.5,
    )

    flip_x: bool = False
    flip_y: bool = False

    alpha: float = 1.0

    layer: int = 0

    uv: tuple[
        float,
        float,
        float,
        float,
    ] = (
        0.0,
        0.0,
        1.0,
        1.0,
    )


class SpriteBatch:
    """
    High-level GPU sprite batch.

    This is the engine-facing sprite API.

    No pygame is used anywhere in this class.

    GPURenderer owns the actual GPU frame lifecycle.
    SpriteBatch only prepares and submits sprite instances.

    Supported:

        - GPU instanced rendering
        - world-space rendering
        - screen-space rendering
        - rotation
        - scaling
        - origin
        - alpha
        - horizontal/vertical flipping
        - UV regions
        - layer ordering
        - CPU-side frustum culling
        - rotation-aware CPU-side frustum culling
        - bulk sprite submission
    """

    __slots__ = (
        "renderer",
        "gpu_batch",
        "initial_capacity",
        "max_sprites",
        "culling",

        "_active",
        "_world_space",
        "_texture",

        "_submitted",
        "_rendered",
        "_culled",
        "_flushes",

        "_sprites",
    )

    def __init__(
        self,
        renderer,
        *,
        initial_capacity: int = 1024,
        max_sprites: int | None = None,
        culling: bool = True,
    ) -> None:
        ThreadContext.assert_main_thread(
            "SpriteBatch.__init__"
        )

        if initial_capacity < 1:
            raise ValueError(
                "initial_capacity must be greater than 0."
            )

        if max_sprites is not None and max_sprites < 1:
            raise ValueError(
                "max_sprites must be greater than 0."
            )

        if max_sprites is None:
            max_sprites = max(
                initial_capacity,
                10000,
            )

        self.renderer = renderer

        self.initial_capacity = int(
            initial_capacity
        )

        self.max_sprites = int(
            max_sprites
        )

        self.culling = bool(culling)

        # ----------------------------------------------------------
        # Actual GPU batch
        # ----------------------------------------------------------

        self.gpu_batch: GPUSpriteBatch = (
            renderer.gpu.sprite_batch
        )

        # ----------------------------------------------------------
        # State
        # ----------------------------------------------------------

        self._active = False
        self._world_space = False
        self._texture = None

        # ----------------------------------------------------------
        # Statistics
        # ----------------------------------------------------------

        self._submitted = 0
        self._rendered = 0
        self._culled = 0
        self._flushes = 0

        # ----------------------------------------------------------
        # High-level sprite storage
        #
        # Each entry is:
        #
        #     (
        #         layer,
        #         gpu_instance_data,
        #     )
        #
        # Layer sorting happens before GPU submission.
        # ----------------------------------------------------------

        self._sprites: list[
            tuple[int, tuple]
        ] = []

    # ==========================================================
    # PROPERTIES
    # ==========================================================

    @property
    def count(self) -> int:
        """
        Number of sprites currently queued.
        """

        return len(self._sprites)

    @property
    def active(self) -> bool:
        return self._active

    @property
    def world_space(self) -> bool:
        return self._world_space

    @property
    def submitted(self) -> int:
        return self._submitted

    @property
    def rendered(self) -> int:
        return self._rendered

    @property
    def culled(self) -> int:
        return self._culled

    @property
    def flushes(self) -> int:
        return self._flushes

    # ==========================================================
    # BEGIN
    # ==========================================================

    def begin(
        self,
        texture=None,
        *,
        world_space: bool = False,
    ) -> None:
        """
        Begin collecting sprites.

        A texture is required because the current GPU batch
        supports one texture per batch/frame.
        """

        ThreadContext.assert_main_thread(
            "SpriteBatch.begin"
        )

        if self._active:
            raise RuntimeError(
                "SpriteBatch.begin() called while batch is active."
            )

        if texture is None:
            raise ValueError(
                "SpriteBatch.begin() requires a GPUTexture."
            )

        self._active = True
        self._world_space = bool(
            world_space
        )
        self._texture = texture

        self._submitted = 0
        self._rendered = 0
        self._culled = 0
        self._flushes = 0

        self._sprites.clear()

        self.gpu_batch.begin(
            texture
        )

    # ==========================================================
    # CANCEL
    # ==========================================================

    def cancel(self) -> None:
        """
        Cancel the current batch without rendering it.
        """

        ThreadContext.assert_main_thread(
            "SpriteBatch.cancel"
        )

        self._active = False
        self._world_space = False
        self._texture = None

        self._sprites.clear()

    # ==========================================================
    # VALIDATION
    # ==========================================================

    @staticmethod
    def _validate_values(
        *,
        width: float | None,
        height: float | None,
        scale: float,
        origin: tuple[float, float],
        alpha: float,
        uv: tuple[
            float,
            float,
            float,
            float,
        ],
    ) -> None:
        if width is not None and width <= 0:
            raise ValueError(
                "width must be greater than 0."
            )

        if height is not None and height <= 0:
            raise ValueError(
                "height must be greater than 0."
            )

        if scale <= 0:
            raise ValueError(
                "scale must be greater than 0."
            )

        if len(origin) != 2:
            raise ValueError(
                "origin must contain exactly two values."
            )

        if not 0.0 <= alpha <= 1.0:
            raise ValueError(
                "alpha must be between 0.0 and 1.0."
            )

        if len(uv) != 4:
            raise ValueError(
                "uv must contain exactly four values."
            )

    # ==========================================================
    # TEXTURE DIMENSIONS
    # ==========================================================

    @staticmethod
    def _get_texture_dimensions(
        texture,
    ) -> tuple[float, float]:
        """
        Read dimensions directly from GPUTexture.

        No SDL surface and no pygame surface are required.
        """

        width = getattr(
            texture,
            "width",
            None,
        )

        height = getattr(
            texture,
            "height",
            None,
        )

        if width is None or height is None:
            raise TypeError(
                "GPUTexture must expose width and height."
            )

        return (
            float(width),
            float(height),
        )

    # ==========================================================
    # VISIBILITY
    # ==========================================================

    def _is_visible(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        origin: tuple[float, float],
        rotation: float = 0.0,
    ) -> bool:
        """
        CPU-side sprite visibility test.

        The test uses the exact axis-aligned bounding box of the
        rotated sprite.

        The four sprite corners are transformed around the
        configured origin. This makes the culling correct for:

            - rotation
            - arbitrary origin
            - world-space sprites
            - screen-space sprites
            - camera zoom

        The result is conservative because it tests the rotated
        sprite's AABB. Therefore a sprite is never incorrectly
        removed while any part of its rotated bounds is visible.

        No SDL or GPU operations are performed here.
        """

        # ------------------------------------------------------
        # World -> screen
        # ------------------------------------------------------

        if self._world_space:
            x, y = self.renderer.world_to_screen(
                x,
                y,
            )

            camera = getattr(
                self.renderer,
                "camera",
                None,
            )

            if camera is not None:
                zoom = float(
                    camera.zoom
                )

                width *= zoom
                height *= zoom

        # ------------------------------------------------------
        # Fast path for non-rotated sprites.
        #
        # This avoids trigonometric calculations for the common
        # case where rotation is zero.
        # ------------------------------------------------------

        if rotation == 0.0:
            left = (
                x
                - width * origin[0]
            )

            top = (
                y
                - height * origin[1]
            )

            right = (
                left
                + width
            )

            bottom = (
                top
                + height
            )

            return not (
                right < 0.0
                or bottom < 0.0
                or left >= self.renderer.width
                or top >= self.renderer.height
            )

        # ------------------------------------------------------
        # Rotated bounding box.
        #
        # Sprite local coordinates are defined relative to the
        # sprite position, which is the configured origin.
        #
        # Example for origin=(0.5, 0.5):
        #
        #       (-w/2,-h/2) -------- (w/2,-h/2)
        #             |                  |
        #             |       center     |
        #             |                  |
        #       (-w/2, h/2) -------- (w/2, h/2)
        #
        # The corners are rotated around (x, y).
        # ------------------------------------------------------

        ox, oy = origin

        left_local = (
            -width * ox
        )

        right_local = (
            width * (1.0 - ox)
        )

        top_local = (
            -height * oy
        )

        bottom_local = (
            height * (1.0 - oy)
        )

        cos_rotation = math.cos(
            rotation
        )

        sin_rotation = math.sin(
            rotation
        )

        # ------------------------------------------------------
        # Rotate all four corners.
        #
        # For:
        #
        #   rx = lx * cos - ly * sin
        #   ry = lx * sin + ly * cos
        #
        # We only need min/max values, so no temporary tuples
        # or lists are created.
        # ------------------------------------------------------

        rx = (
            left_local * cos_rotation
            - top_local * sin_rotation
        )

        ry = (
            left_local * sin_rotation
            + top_local * cos_rotation
        )

        min_x = rx
        max_x = rx
        min_y = ry
        max_y = ry

        rx = (
            right_local * cos_rotation
            - top_local * sin_rotation
        )

        ry = (
            right_local * sin_rotation
            + top_local * cos_rotation
        )

        if rx < min_x:
            min_x = rx

        if rx > max_x:
            max_x = rx

        if ry < min_y:
            min_y = ry

        if ry > max_y:
            max_y = ry

        rx = (
            left_local * cos_rotation
            - bottom_local * sin_rotation
        )

        ry = (
            left_local * sin_rotation
            + bottom_local * cos_rotation
        )

        if rx < min_x:
            min_x = rx

        if rx > max_x:
            max_x = rx

        if ry < min_y:
            min_y = ry

        if ry > max_y:
            max_y = ry

        rx = (
            right_local * cos_rotation
            - bottom_local * sin_rotation
        )

        ry = (
            right_local * sin_rotation
            + bottom_local * cos_rotation
        )

        if rx < min_x:
            min_x = rx

        if rx > max_x:
            max_x = rx

        if ry < min_y:
            min_y = ry

        if ry > max_y:
            max_y = ry

        # ------------------------------------------------------
        # Convert local bounding box to screen coordinates.
        # ------------------------------------------------------

        left = x + min_x
        right = x + max_x

        top = y + min_y
        bottom = y + max_y

        return not (
            right < 0.0
            or bottom < 0.0
            or left >= self.renderer.width
            or top >= self.renderer.height
        )

    # ==========================================================
    # STORE SPRITE
    # ==========================================================

    def _store_sprite(
        self,
        *,
        layer: int,
        x: float,
        y: float,
        width: float,
        height: float,
        rotation: float,
        origin: tuple[float, float],
        alpha: float,
        flip_x: bool,
        flip_y: bool,
        uv: tuple[
            float,
            float,
            float,
            float,
        ],
    ) -> None:
        """
        Store one already prepared sprite.

        Layer information stays attached to the sprite until
        end(), where all sprites are sorted before GPU submission.
        """

        self._sprites.append(
            (
                int(layer),
                (
                    float(x),
                    float(y),
                    float(width),
                    float(height),
                    float(rotation),
                    float(origin[0]),
                    float(origin[1]),
                    float(alpha),
                    bool(flip_x),
                    bool(flip_y),
                    float(uv[0]),
                    float(uv[1]),
                    float(uv[2]),
                    float(uv[3]),
                ),
            )
        )

        self._submitted += 1

    # ==========================================================
    # ADD
    # ==========================================================

    def add(
        self,
        texture=None,
        x: float = 0.0,
        y: float = 0.0,
        *,
        width: float | None = None,
        height: float | None = None,
        rotation: float = 0.0,
        scale: float = 1.0,
        origin: tuple[float, float] = (
            0.5,
            0.5,
        ),
        flip_x: bool = False,
        flip_y: bool = False,
        alpha: float = 1.0,
        layer: int = 0,
        uv: tuple[
            float,
            float,
            float,
            float,
        ] = (
            0.0,
            0.0,
            1.0,
            1.0,
        ),
    ) -> None:
        """
        Add one sprite to the batch.
        """

        ThreadContext.assert_main_thread(
            "SpriteBatch.add"
        )

        if not self._active:
            raise RuntimeError(
                "SpriteBatch.add() requires an active batch. "
                "Call begin(texture) first."
            )

        if texture is not None:
            if texture is not self._texture:
                raise RuntimeError(
                    "All sprites in one SpriteBatch must use "
                    "the texture passed to begin()."
                )

        if self._texture is None:
            raise RuntimeError(
                "No texture selected."
            )

        self._validate_values(
            width=width,
            height=height,
            scale=scale,
            origin=origin,
            alpha=alpha,
            uv=uv,
        )

        # ------------------------------------------------------
        # Default dimensions
        # ------------------------------------------------------

        texture_width, texture_height = (
            self._get_texture_dimensions(
                self._texture
            )
        )

        if width is None:
            width = texture_width

        if height is None:
            height = texture_height

        # ------------------------------------------------------
        # Apply scale
        # ------------------------------------------------------

        final_width = (
            float(width)
            * float(scale)
        )

        final_height = (
            float(height)
            * float(scale)
        )

        # ------------------------------------------------------
        # Culling
        # ------------------------------------------------------

        if self.culling:
            if not self._is_visible(
                float(x),
                float(y),
                final_width,
                final_height,
                origin,
                float(rotation),
            ):
                self._culled += 1
                return

        # ------------------------------------------------------
        # Store
        # ------------------------------------------------------

        self._store_sprite(
            layer=layer,
            x=x,
            y=y,
            width=final_width,
            height=final_height,
            rotation=rotation,
            origin=origin,
            alpha=alpha,
            flip_x=flip_x,
            flip_y=flip_y,
            uv=uv,
        )

    # ==========================================================
    # FAST ADD
    # ==========================================================

    def add_fast(
        self,
        texture=None,
        x: float = 0.0,
        y: float = 0.0,
        *,
        width: float | None = None,
        height: float | None = None,
        rotation: float = 0.0,
        scale: float = 1.0,
        origin: tuple[float, float] = (
            0.5,
            0.5,
        ),
        flip_x: bool = False,
        flip_y: bool = False,
        alpha: float = 1.0,
        layer: int = 0,
        uv: tuple[
            float,
            float,
            float,
            float,
        ] = (
            0.0,
            0.0,
            1.0,
            1.0,
        ),
    ) -> None:
        """
        Fast sprite submission.

        This still performs culling because culling is part of
        the SpriteBatch contract.
        """

        if not self._active:
            raise RuntimeError(
                "SpriteBatch.add_fast() requires an active batch."
            )

        if (
            texture is not None
            and texture is not self._texture
        ):
            raise RuntimeError(
                "SpriteBatch.add_fast() received a different texture."
            )

        if self._texture is None:
            raise RuntimeError(
                "No texture selected."
            )

        if width is None or height is None:
            texture_width, texture_height = (
                self._get_texture_dimensions(
                    self._texture
                )
            )

            if width is None:
                width = texture_width

            if height is None:
                height = texture_height

        final_width = (
            float(width)
            * float(scale)
        )

        final_height = (
            float(height)
            * float(scale)
        )

        if self.culling:
            if not self._is_visible(
                float(x),
                float(y),
                final_width,
                final_height,
                origin,
                float(rotation),
            ):
                self._culled += 1
                return

        self._store_sprite(
            layer=layer,
            x=x,
            y=y,
            width=final_width,
            height=final_height,
            rotation=rotation,
            origin=origin,
            alpha=alpha,
            flip_x=flip_x,
            flip_y=flip_y,
            uv=uv,
        )

    # ==========================================================
    # BULK
    # ==========================================================

    def add_many(
        self,
        sprites,
        *,
        workers: int | None = None,
    ) -> int:
        """
        Add many already prepared sprites.

        Supported input formats:

        14 values:
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

        15 values:
            Same as above plus:

                layer

        When the layer is omitted, layer 0 is used.

        Sprites are stored in the high-level queue first.
        Layer sorting is performed by end(), together with all
        other SpriteBatch submissions.

        Rotation-aware culling is applied to every sprite.
        """

        if not self._active:
            raise RuntimeError(
                "SpriteBatch.add_many() requires an active batch."
            )

        if not hasattr(
            sprites,
            "__len__",
        ):
            sprites = list(sprites)

        if not sprites:
            return 0

        # ------------------------------------------------------
        # Normalize and cull.
        #
        # Layer information remains attached to the sprite.
        # ------------------------------------------------------

        added = 0

        for sprite in sprites:
            sprite_length = len(sprite)

            if sprite_length not in (14, 15):
                raise ValueError(
                    "SpriteBatch.add_many() expects sprites "
                    "with 14 or 15 values."
                )

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
            ) = sprite[:14]

            layer = (
                sprite[14]
                if sprite_length == 15
                else 0
            )

            x = float(x)
            y = float(y)
            width = float(width)
            height = float(height)
            rotation = float(rotation)
            origin_x = float(origin_x)
            origin_y = float(origin_y)
            alpha = float(alpha)

            uv_x = float(uv_x)
            uv_y = float(uv_y)
            uv_width = float(uv_width)
            uv_height = float(uv_height)

            if self.culling:
                if not self._is_visible(
                    x,
                    y,
                    width,
                    height,
                    (
                        origin_x,
                        origin_y,
                    ),
                    rotation,
                ):
                    self._culled += 1
                    continue

            self._store_sprite(
                layer=int(layer),
                x=x,
                y=y,
                width=width,
                height=height,
                rotation=rotation,
                origin=(
                    origin_x,
                    origin_y,
                ),
                alpha=alpha,
                flip_x=bool(flip_x),
                flip_y=bool(flip_y),
                uv=(
                    uv_x,
                    uv_y,
                    uv_width,
                    uv_height,
                ),
            )

            added += 1

        return added

    # ==========================================================
    # END
    # ==========================================================

    def end(self) -> int:
        """
        Finalize the high-level batch.

        This does NOT submit the GPU command buffer.

        GPURenderer.end_frame() owns the actual GPU submission.

        Layer ordering:

            smaller layer -> rendered first
            larger layer  -> rendered later / on top

        Python's list.sort() is stable, so sprites with the same
        layer preserve their original submission order.
        """

        ThreadContext.assert_main_thread(
            "SpriteBatch.end"
        )

        if not self._active:
            raise RuntimeError(
                "SpriteBatch.end() called without an active batch."
            )

        try:
            if not self._sprites:
                self._rendered = 0
                return 0

            # --------------------------------------------------
            # Layer ordering
            #
            # Stable sort:
            #
            #   layer 0
            #   layer 1
            #   layer 2
            #
            # Equal layers retain submission order.
            # --------------------------------------------------

            if len(self._sprites) > 1:
                first_layer = (
                    self._sprites[0][0]
                )

                multiple_layers = any(
                    layer != first_layer
                    for layer, _ in self._sprites[1:]
                )

                if multiple_layers:
                    self._sprites.sort(
                        key=lambda item: item[0]
                    )

            # --------------------------------------------------
            # Strip layer information.
            # --------------------------------------------------

            gpu_sprites = [
                sprite
                for _, sprite in self._sprites
            ]

            # --------------------------------------------------
            # Submit the final ordered data to the GPU batch.
            # --------------------------------------------------

            self.gpu_batch.add_many(
                gpu_sprites
            )

            self._rendered = len(
                gpu_sprites
            )

            self._flushes += 1

            return self._rendered

        finally:
            self._active = False
            self._world_space = False
            self._texture = None
            self._sprites.clear()

    # ==========================================================
    # GPU FRAME INTEGRATION
    # ==========================================================

    def render_into(
        self,
        command_buffer,
    ) -> int:
        """
        Upload prepared sprite instances into the active GPU
        command buffer.
        """

        return self.gpu_batch.render_into(
            command_buffer
        )

    def draw_into(
        self,
        render_pass,
    ) -> int:
        """
        Draw prepared sprites into an active GPU render pass.
        """

        return self.gpu_batch.draw_into(
            render_pass
        )

    # ==========================================================
    # COMPATIBILITY DRAW
    # ==========================================================

    def draw(
        self,
        sprites: Iterable[BatchSprite],
        *,
        texture=None,
        world_space: bool = False,
    ) -> int:
        """
        Convenience API for drawing BatchSprite objects.
        """

        # ------------------------------------------------------
        # Determine texture from first sprite when omitted.
        # ------------------------------------------------------

        if texture is None:
            sprites = list(sprites)

            if not sprites:
                return 0

            texture = sprites[0].texture

        self.begin(
            texture,
            world_space=world_space,
        )

        try:
            for sprite in sprites:
                self.add_fast(
                    sprite.texture,
                    sprite.x,
                    sprite.y,
                    width=sprite.width,
                    height=sprite.height,
                    rotation=sprite.rotation,
                    scale=sprite.scale,
                    origin=sprite.origin,
                    flip_x=sprite.flip_x,
                    flip_y=sprite.flip_y,
                    alpha=sprite.alpha,
                    layer=sprite.layer,
                    uv=sprite.uv,
                )

            return self.end()

        except Exception:
            self.cancel()
            raise

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(self) -> None:
        """
        Clear the high-level batch.
        """

        ThreadContext.assert_main_thread(
            "SpriteBatch.clear"
        )

        self._sprites.clear()

        self._submitted = 0
        self._rendered = 0
        self._culled = 0
        self._flushes = 0

        self._active = False
        self._world_space = False
        self._texture = None
