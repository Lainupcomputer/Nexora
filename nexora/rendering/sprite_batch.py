from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pygame

from nexora.threading.context import ThreadContext


@dataclass(slots=True)
class BatchSprite:
    """
    Compatibility container for one sprite.

    The hot path of SpriteBatch does not create these objects.
    """

    texture: pygame.Surface
    x: float
    y: float
    width: float | None = None
    height: float | None = None
    rotation: float = 0.0
    scale: float = 1.0
    origin: tuple[float, float] = (0.5, 0.5)
    flip_x: bool = False
    flip_y: bool = False
    alpha: int | None = None
    layer: int = 0


class SpriteBatch:
    """
    High-performance sprite batcher.

    Rendering paths:

        1. Static fast path
           All sprites share the exact same render state.

        2. Cached transform path
           Sprites can have different transforms, while transformed
           surfaces are resolved through the renderer cache.

        3. General path
           Supports layers and arbitrary sprite properties.

    All pygame/SDL operations remain on the main thread.
    """

    __slots__ = (
        "renderer",
        "initial_capacity",
        "max_sprites",
        "culling",

        "_textures",
        "_xs",
        "_ys",
        "_widths",
        "_heights",
        "_rotations",
        "_scales",
        "_origins",
        "_flip_x",
        "_flip_y",
        "_alphas",
        "_layers",

        "_count",
        "_active",
        "_world_space",

        "_submitted",
        "_rendered",
        "_culled",
        "_flushes",

        "_fast_mode",
        "_fast_texture",
        "_fast_width",
        "_fast_height",
        "_fast_rotation",
        "_fast_scale",
        "_fast_origin",
        "_fast_flip_x",
        "_fast_flip_y",
        "_fast_alpha",
        "_fast_layer",

        "_fast_draws",
        "_general_draws",

        "_local_surface_cache",
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

        if max_sprites is not None:
            initial_capacity = min(
                initial_capacity,
                max_sprites,
            )

        self.renderer = renderer
        self.initial_capacity = initial_capacity
        self.max_sprites = max_sprites
        self.culling = bool(culling)

        self._textures: list[pygame.Surface | None] = (
            [None] * initial_capacity
        )
        self._xs: list[float] = (
            [0.0] * initial_capacity
        )
        self._ys: list[float] = (
            [0.0] * initial_capacity
        )
        self._widths: list[float | None] = (
            [None] * initial_capacity
        )
        self._heights: list[float | None] = (
            [None] * initial_capacity
        )
        self._rotations: list[float] = (
            [0.0] * initial_capacity
        )
        self._scales: list[float] = (
            [1.0] * initial_capacity
        )
        self._origins: list[tuple[float, float]] = (
            [(0.5, 0.5)] * initial_capacity
        )
        self._flip_x: list[bool] = (
            [False] * initial_capacity
        )
        self._flip_y: list[bool] = (
            [False] * initial_capacity
        )
        self._alphas: list[int | None] = (
            [None] * initial_capacity
        )
        self._layers: list[int] = (
            [0] * initial_capacity
        )

        self._count = 0
        self._active = False
        self._world_space = False

        self._submitted = 0
        self._rendered = 0
        self._culled = 0
        self._flushes = 0

        self._fast_mode = True

        self._fast_texture: pygame.Surface | None = None
        self._fast_width: float | None = None
        self._fast_height: float | None = None
        self._fast_rotation = 0.0
        self._fast_scale = 1.0
        self._fast_origin = (0.5, 0.5)
        self._fast_flip_x = False
        self._fast_flip_y = False
        self._fast_alpha: int | None = None
        self._fast_layer = 0

        self._fast_draws: list[
            tuple[pygame.Surface, tuple[int, int]]
        ] = []

        self._general_draws: list[
            tuple[pygame.Surface, tuple[int, int]]
        ] = []

        # Per-batch transformed surface cache.
        #
        # Renderer already owns the global LRU cache.
        # This local cache avoids repeatedly constructing identical
        # cache keys and repeatedly entering Renderer._get_cached_sprite()
        # during one batch.
        self._local_surface_cache: dict[
            tuple,
            pygame.Surface,
        ] = {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        return self._count

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

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def begin(
        self,
        *,
        world_space: bool = False,
    ) -> None:
        ThreadContext.assert_main_thread(
            "SpriteBatch.begin"
        )

        if self._active:
            raise RuntimeError(
                "SpriteBatch.begin() called while batch is active."
            )

        self._active = True
        self._world_space = bool(world_space)

        self._count = 0
        self._submitted = 0
        self._rendered = 0
        self._culled = 0
        self._flushes = 0

        self._fast_mode = True

        self._fast_texture = None
        self._fast_width = None
        self._fast_height = None
        self._fast_rotation = 0.0
        self._fast_scale = 1.0
        self._fast_origin = (0.5, 0.5)
        self._fast_flip_x = False
        self._fast_flip_y = False
        self._fast_alpha = None
        self._fast_layer = 0

        self._fast_draws.clear()
        self._general_draws.clear()
        self._local_surface_cache.clear()

    def cancel(self) -> None:
        ThreadContext.assert_main_thread(
            "SpriteBatch.cancel"
        )

        self._active = False
        self._count = 0

        self._fast_draws.clear()
        self._general_draws.clear()
        self._local_surface_cache.clear()

    # ------------------------------------------------------------------
    # Capacity
    # ------------------------------------------------------------------

    def _ensure_capacity(
        self,
        required: int,
    ) -> None:
        if required <= len(self._textures):
            return

        if (
            self.max_sprites is not None
            and required > self.max_sprites
        ):
            raise RuntimeError(
                "SpriteBatch capacity exceeded: "
                f"maximum is {self.max_sprites} sprites."
            )

        old_capacity = len(self._textures)

        new_capacity = max(
            required,
            old_capacity * 2,
        )

        if self.max_sprites is not None:
            new_capacity = min(
                new_capacity,
                self.max_sprites,
            )

        growth = new_capacity - old_capacity

        self._textures.extend(
            [None] * growth
        )
        self._xs.extend(
            [0.0] * growth
        )
        self._ys.extend(
            [0.0] * growth
        )
        self._widths.extend(
            [None] * growth
        )
        self._heights.extend(
            [None] * growth
        )
        self._rotations.extend(
            [0.0] * growth
        )
        self._scales.extend(
            [1.0] * growth
        )
        self._origins.extend(
            [(0.5, 0.5)] * growth
        )
        self._flip_x.extend(
            [False] * growth
        )
        self._flip_y.extend(
            [False] * growth
        )
        self._alphas.extend(
            [None] * growth
        )
        self._layers.extend(
            [0] * growth
        )

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    def add(
        self,
        texture: pygame.Surface,
        x: float,
        y: float,
        *,
        width: float | None = None,
        height: float | None = None,
        rotation: float = 0.0,
        scale: float = 1.0,
        origin: tuple[float, float] = (0.5, 0.5),
        flip_x: bool = False,
        flip_y: bool = False,
        alpha: int | None = None,
        layer: int = 0,
    ) -> None:
        ThreadContext.assert_main_thread(
            "SpriteBatch.add"
        )

        if not self._active:
            raise RuntimeError(
                "SpriteBatch.add() requires an active batch. "
                "Call begin() first."
            )

        if not isinstance(texture, pygame.Surface):
            raise TypeError(
                "texture must be a pygame.Surface."
            )

        self._validate_values(
            width=width,
            height=height,
            scale=scale,
            origin=origin,
        )

        self._add_internal(
            texture,
            x,
            y,
            width=width,
            height=height,
            rotation=rotation,
            scale=scale,
            origin=origin,
            flip_x=flip_x,
            flip_y=flip_y,
            alpha=alpha,
            layer=layer,
        )

    def add_fast(
        self,
        texture: pygame.Surface,
        x: float,
        y: float,
        *,
        width: float | None = None,
        height: float | None = None,
        rotation: float = 0.0,
        scale: float = 1.0,
        origin: tuple[float, float] = (0.5, 0.5),
        flip_x: bool = False,
        flip_y: bool = False,
        alpha: int | None = None,
        layer: int = 0,
    ) -> None:
        if not self._active:
            raise RuntimeError(
                "SpriteBatch.add_fast() requires an active batch. "
                "Call begin() first."
            )

        self._add_internal(
            texture,
            x,
            y,
            width=width,
            height=height,
            rotation=rotation,
            scale=scale,
            origin=origin,
            flip_x=flip_x,
            flip_y=flip_y,
            alpha=alpha,
            layer=layer,
        )

    def _add_internal(
        self,
        texture: pygame.Surface,
        x: float,
        y: float,
        *,
        width: float | None,
        height: float | None,
        rotation: float,
        scale: float,
        origin: tuple[float, float],
        flip_x: bool,
        flip_y: bool,
        alpha: int | None,
        layer: int,
    ) -> None:
        index = self._count

        self._ensure_capacity(
            index + 1
        )

        self._textures[index] = texture
        self._xs[index] = x
        self._ys[index] = y

        self._widths[index] = width
        self._heights[index] = height

        self._rotations[index] = rotation
        self._scales[index] = scale

        self._origins[index] = origin

        self._flip_x[index] = flip_x
        self._flip_y[index] = flip_y

        self._alphas[index] = alpha
        self._layers[index] = layer

        self._count = index + 1
        self._submitted += 1

        if self._fast_mode:
            if self._fast_texture is None:
                self._fast_texture = texture
                self._fast_width = width
                self._fast_height = height
                self._fast_rotation = rotation
                self._fast_scale = scale
                self._fast_origin = origin
                self._fast_flip_x = flip_x
                self._fast_flip_y = flip_y
                self._fast_alpha = alpha
                self._fast_layer = layer

            elif not self._matches_fast_state(
                texture,
                width,
                height,
                rotation,
                scale,
                origin,
                flip_x,
                flip_y,
                alpha,
                layer,
            ):
                self._fast_mode = False

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_values(
        *,
        width: float | None,
        height: float | None,
        scale: float,
        origin: tuple[float, float],
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

    def _matches_fast_state(
        self,
        texture: pygame.Surface,
        width: float | None,
        height: float | None,
        rotation: float,
        scale: float,
        origin: tuple[float, float],
        flip_x: bool,
        flip_y: bool,
        alpha: int | None,
        layer: int,
    ) -> bool:
        return (
            texture is self._fast_texture
            and width == self._fast_width
            and height == self._fast_height
            and rotation == self._fast_rotation
            and scale == self._fast_scale
            and origin == self._fast_origin
            and flip_x == self._fast_flip_x
            and flip_y == self._fast_flip_y
            and alpha == self._fast_alpha
            and layer == self._fast_layer
        )

    # ------------------------------------------------------------------
    # Dimensions
    # ------------------------------------------------------------------

    @staticmethod
    def _get_dimensions(
        texture: pygame.Surface,
        width: float | None,
        height: float | None,
        scale: float,
    ) -> tuple[int, int]:
        if width is None:
            width = texture.get_width()

        if height is None:
            height = texture.get_height()

        return (
            max(
                1,
                round(width * scale),
            ),
            max(
                1,
                round(height * scale),
            ),
        )

    def _get_world_dimensions(
        self,
        texture: pygame.Surface,
        width: float | None,
        height: float | None,
        scale: float,
    ) -> tuple[int, int]:
        if width is None:
            width = texture.get_width()

        if height is None:
            height = texture.get_height()

        zoom = self.renderer.camera.zoom

        return (
            max(
                1,
                round(
                    width
                    * scale
                    * zoom
                ),
            ),
            max(
                1,
                round(
                    height
                    * scale
                    * zoom
                ),
            ),
        )

    # ------------------------------------------------------------------
    # Culling
    # ------------------------------------------------------------------

    def _is_visible_screen(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        origin: tuple[float, float],
    ) -> bool:
        surface = self.renderer.surface

        left = x - width * origin[0]
        top = y - height * origin[1]

        right = left + width
        bottom = top + height

        return not (
            right < 0
            or bottom < 0
            or left >= surface.get_width()
            or top >= surface.get_height()
        )

    def _is_visible_world(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        origin: tuple[float, float],
    ) -> bool:
        renderer = self.renderer

        screen_x, screen_y = (
            renderer.world_to_screen(
                x,
                y,
            )
        )

        zoom = renderer.camera.zoom

        return self._is_visible_screen(
            screen_x,
            screen_y,
            width * zoom,
            height * zoom,
            origin,
        )

    # ------------------------------------------------------------------
    # Transform cache
    # ------------------------------------------------------------------

    def _get_local_cached_surface(
        self,
        texture: pygame.Surface,
        width: int,
        height: int,
        rotation: float,
        flip_x: bool,
        flip_y: bool,
    ) -> pygame.Surface:
        """
        Resolve a transformed surface.

        The cache is local to the current batch. This is intentionally
        separate from Renderer._sprite_cache because the renderer cache
        is shared across the entire frame/application.
        """

        key = (
            id(texture),
            width,
            height,
            self.renderer._quantize_rotation(
                rotation
            ),
            bool(flip_x),
            bool(flip_y),
        )

        cached = self._local_surface_cache.get(
            key
        )

        if cached is not None:
            return cached

        cached = self.renderer._get_cached_sprite(
            texture,
            width,
            height,
            rotation,
            flip_x,
            flip_y,
        )

        self._local_surface_cache[key] = cached

        return cached

    # ------------------------------------------------------------------
    # End
    # ------------------------------------------------------------------

    def end(self) -> int:
        ThreadContext.assert_main_thread(
            "SpriteBatch.end"
        )

        if not self._active:
            raise RuntimeError(
                "SpriteBatch.end() called without an active batch."
            )

        try:
            if self._count == 0:
                return 0

            if self._fast_mode:
                rendered = self._render_fast()
            else:
                rendered = self._render_general()

            self._rendered = rendered
            self._flushes += 1

            return rendered

        finally:
            self._active = False
            self._count = 0

    # ------------------------------------------------------------------
    # Static fast path
    # ------------------------------------------------------------------

    def _render_fast(self) -> int:
        texture = self._fast_texture

        if texture is None:
            return 0

        if self._world_space:
            width, height = (
                self._get_world_dimensions(
                    texture,
                    self._fast_width,
                    self._fast_height,
                    self._fast_scale,
                )
            )
        else:
            width, height = (
                self._get_dimensions(
                    texture,
                    self._fast_width,
                    self._fast_height,
                    self._fast_scale,
                )
            )

        source = self._get_local_cached_surface(
            texture,
            width,
            height,
            self._fast_rotation,
            self._fast_flip_x,
            self._fast_flip_y,
        )

        if self._fast_alpha is not None:
            alpha = max(
                0,
                min(
                    255,
                    int(self._fast_alpha),
                ),
            )

            source = source.copy()
            source.set_alpha(alpha)

        origin = self._fast_origin

        draws = self._fast_draws
        draws.clear()

        append = draws.append

        source_width = source.get_width()
        source_height = source.get_height()

        if self._world_space:
            world_to_screen = (
                self.renderer.world_to_screen
            )

            for index in range(
                self._count
            ):
                screen_x, screen_y = (
                    world_to_screen(
                        self._xs[index],
                        self._ys[index],
                    )
                )

                if self.culling:
                    if not self._is_visible_screen(
                        screen_x,
                        screen_y,
                        source_width,
                        source_height,
                        origin,
                    ):
                        self._culled += 1
                        continue

                append(
                    (
                        source,
                        (
                            round(
                                screen_x
                                - source_width
                                * origin[0]
                            ),
                            round(
                                screen_y
                                - source_height
                                * origin[1]
                            ),
                        ),
                    )
                )

        else:
            for index in range(
                self._count
            ):
                x = self._xs[index]
                y = self._ys[index]

                if self.culling:
                    if not self._is_visible_screen(
                        x,
                        y,
                        source_width,
                        source_height,
                        origin,
                    ):
                        self._culled += 1
                        continue

                append(
                    (
                        source,
                        (
                            round(
                                x
                                - source_width
                                * origin[0]
                            ),
                            round(
                                y
                                - source_height
                                * origin[1]
                            ),
                        ),
                    )
                )

        if not draws:
            return 0

        self.renderer.surface.blits(
            draws,
            doreturn=False,
        )

        return len(draws)

    # ------------------------------------------------------------------
    # General cached path
    # ------------------------------------------------------------------

    def _render_general(self) -> int:
        """
        Render arbitrary sprites using the cached-transform path.

        Important optimization:
        - no per-frame grouping
        - no sorting unless layers actually differ
        - transformed surfaces are resolved through a local cache
        - one final pygame Surface.blits() call
        """

        draws = self._general_draws
        draws.clear()

        append = draws.append

        renderer = self.renderer
        surface = renderer.surface

        textures = self._textures
        xs = self._xs
        ys = self._ys
        widths = self._widths
        heights = self._heights
        rotations = self._rotations
        scales = self._scales
        origins = self._origins
        flip_x = self._flip_x
        flip_y = self._flip_y
        alphas = self._alphas
        layers = self._layers

        count = self._count
        world_space = self._world_space
        culling = self.culling

        rendered = 0
        culled = 0

        # Only allocate/sort indices when actual layer ordering
        # requires it.
        multiple_layers = False

        if count > 1:
            first_layer = layers[0]

            for index in range(
                1,
                count,
            ):
                if layers[index] != first_layer:
                    multiple_layers = True
                    break

        if multiple_layers:
            indices = list(
                range(count)
            )
            indices.sort(
                key=layers.__getitem__
            )
        else:
            indices = range(count)

        if world_space:
            world_to_screen = (
                renderer.world_to_screen
            )
            zoom = renderer.camera.zoom

            for index in indices:
                texture = textures[index]

                if texture is None:
                    continue

                width = widths[index]
                height = heights[index]
                scale = scales[index]

                if width is None:
                    base_width = (
                        texture.get_width()
                    )
                else:
                    base_width = width

                if height is None:
                    base_height = (
                        texture.get_height()
                    )
                else:
                    base_height = height

                final_width = max(
                    1,
                    round(
                        base_width
                        * scale
                        * zoom
                    ),
                )

                final_height = max(
                    1,
                    round(
                        base_height
                        * scale
                        * zoom
                    ),
                )

                origin = origins[index]

                screen_x, screen_y = (
                    world_to_screen(
                        xs[index],
                        ys[index],
                    )
                )

                if culling:
                    if not self._is_visible_screen(
                        screen_x,
                        screen_y,
                        final_width,
                        final_height,
                        origin,
                    ):
                        culled += 1
                        continue

                source = (
                    self._get_local_cached_surface(
                        texture,
                        final_width,
                        final_height,
                        rotations[index],
                        flip_x[index],
                        flip_y[index],
                    )
                )

                alpha = alphas[index]

                if alpha is not None:
                    source = source.copy()
                    source.set_alpha(
                        max(
                            0,
                            min(
                                255,
                                int(alpha),
                            ),
                        )
                    )

                source_width = (
                    source.get_width()
                )
                source_height = (
                    source.get_height()
                )

                append(
                    (
                        source,
                        (
                            round(
                                screen_x
                                - source_width
                                * origin[0]
                            ),
                            round(
                                screen_y
                                - source_height
                                * origin[1]
                            ),
                        ),
                    )
                )

                rendered += 1

        else:
            for index in indices:
                texture = textures[index]

                if texture is None:
                    continue

                width = widths[index]
                height = heights[index]
                scale = scales[index]

                if width is None:
                    base_width = (
                        texture.get_width()
                    )
                else:
                    base_width = width

                if height is None:
                    base_height = (
                        texture.get_height()
                    )
                else:
                    base_height = height

                final_width = max(
                    1,
                    round(
                        base_width
                        * scale
                    ),
                )

                final_height = max(
                    1,
                    round(
                        base_height
                        * scale
                    ),
                )

                x = xs[index]
                y = ys[index]
                origin = origins[index]

                if culling:
                    if not self._is_visible_screen(
                        x,
                        y,
                        final_width,
                        final_height,
                        origin,
                    ):
                        culled += 1
                        continue

                source = (
                    self._get_local_cached_surface(
                        texture,
                        final_width,
                        final_height,
                        rotations[index],
                        flip_x[index],
                        flip_y[index],
                    )
                )

                alpha = alphas[index]

                if alpha is not None:
                    source = source.copy()
                    source.set_alpha(
                        max(
                            0,
                            min(
                                255,
                                int(alpha),
                            ),
                        )
                    )

                source_width = (
                    source.get_width()
                )
                source_height = (
                    source.get_height()
                )

                append(
                    (
                        source,
                        (
                            round(
                                x
                                - source_width
                                * origin[0]
                            ),
                            round(
                                y
                                - source_height
                                * origin[1]
                            ),
                        ),
                    )
                )

                rendered += 1

        if draws:
            surface.blits(
                draws,
                doreturn=False,
            )

        self._culled = culled

        return rendered

    # ------------------------------------------------------------------
    # Compatibility API
    # ------------------------------------------------------------------

    def draw(
        self,
        sprites: Iterable[BatchSprite],
        *,
        world_space: bool = False,
    ) -> int:
        self.begin(
            world_space=world_space
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
                )

            return self.end()

        except Exception:
            self.cancel()
            raise

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def clear(self) -> None:
        ThreadContext.assert_main_thread(
            "SpriteBatch.clear"
        )

        self._count = 0

        self._fast_draws.clear()
        self._general_draws.clear()
        self._local_surface_cache.clear()

        self._fast_mode = True

        self._fast_texture = None
        self._fast_width = None
        self._fast_height = None
        self._fast_rotation = 0.0
        self._fast_scale = 1.0
        self._fast_origin = (0.5, 0.5)
        self._fast_flip_x = False
        self._fast_flip_y = False
        self._fast_alpha = None
        self._fast_layer = 0