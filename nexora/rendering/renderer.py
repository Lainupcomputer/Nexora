from __future__ import annotations

from collections import OrderedDict
from typing import Iterable

import pygame

from nexora.rendering.camera import Camera
from nexora.threading.context import ThreadContext
from nexora.rendering.sprite_batch import SpriteBatch

Color = tuple[int, int, int] | tuple[int, int, int, int]


class Renderer:
    """
    Nexora 2D Renderer.

    All rendering operations must run on the main thread because
    pygame/SDL rendering is not thread-safe.

    The renderer supports two coordinate spaces:

    Screen Space:
        rectangle()
        circle()
        line()
        polygon()
        pixel()
        text()
        blit()
        sprite()

    World Space:
        world_rectangle()
        world_circle()
        world_line()
        world_polygon()
        world_sprite()
        world_to_screen()
        screen_to_world()

    Sprite transformations are cached using an LRU cache.
    """

    def __init__(
        self,
        window,
        *,
        sprite_cache_size: int = 2048,
        rotation_cache_step: float = 1.0,
    ) -> None:
        if sprite_cache_size <= 0:
            raise ValueError(
                "sprite_cache_size must be greater than 0."
            )

        if rotation_cache_step <= 0:
            raise ValueError(
                "rotation_cache_step must be greater than 0."
            )

        self.window = window
        self.surface = window.surface

        self.camera = Camera()

        self._clear_color: Color = (25, 25, 30)

        self._font_cache: dict[
            tuple[str | None, int, bool],
            pygame.font.Font,
        ] = {}

        # --------------------------------------------------------------
        # Sprite Transform Cache
        # --------------------------------------------------------------

        self._sprite_cache: OrderedDict[
            tuple,
            pygame.Surface,
        ] = OrderedDict()

        self._sprite_cache_capacity = sprite_cache_size
        self._rotation_cache_step = rotation_cache_step

        # Sprite cache statistics.
        self._sprite_cache_hits = 0
        self._sprite_cache_misses = 0

        self._frame_started = False

        # Reusable default sprite batch.
        self._sprite_batch = SpriteBatch(self)

    # ------------------------------------------------------------------
    # Frame
    # ------------------------------------------------------------------

    def begin_frame(
        self,
        clear_color: Color | None = None,
    ) -> None:
        ThreadContext.assert_main_thread(
            "Renderer.begin_frame"
        )

        if clear_color is None:
            clear_color = self._clear_color

        self.surface.fill(clear_color)

        self._frame_started = True

    def end_frame(self) -> None:
        ThreadContext.assert_main_thread(
            "Renderer.end_frame"
        )

        pygame.display.flip()

        self._frame_started = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def width(self) -> int:
        return self.window.width

    @property
    def height(self) -> int:
        return self.window.height

    @property
    def size(self) -> tuple[int, int]:
        return self.window.width, self.window.height

    @property
    def clear_color(self) -> Color:
        return self._clear_color

    @clear_color.setter
    def clear_color(self, value: Color) -> None:
        self._clear_color = value

    @property
    def sprite_cache_size(self) -> int:
        """
        Number of currently cached transformed sprites.
        """
        return len(self._sprite_cache)

    @property
    def sprite_cache_capacity(self) -> int:
        """
        Maximum number of transformed sprites kept in the cache.
        """
        return self._sprite_cache_capacity

    @property
    def sprite_cache_hits(self) -> int:
        """
        Number of sprite cache hits.
        """
        return self._sprite_cache_hits

    @property
    def sprite_cache_misses(self) -> int:
        """
        Number of sprite cache misses.
        """
        return self._sprite_cache_misses

    @property
    def sprite_cache_hit_rate(self) -> float:
        """
        Sprite cache hit rate as a value between 0.0 and 1.0.
        """

        total = (
            self._sprite_cache_hits
            + self._sprite_cache_misses
        )

        if total == 0:
            return 0.0

        return (
            self._sprite_cache_hits
            / total
        )

    @property
    def sprite_batch(self) -> SpriteBatch:
        """
        Default reusable SpriteBatch instance.
        """
        return self._sprite_batch

    def create_sprite_batch(
        self,
        *,
        initial_capacity: int = 1024,
        max_sprites: int = 100_000,
        culling: bool = True,
    ) -> SpriteBatch:
        """
        Create an additional SpriteBatch.
        """

        return SpriteBatch(
            self,
            initial_capacity=initial_capacity,
            max_sprites=max_sprites,
            culling=culling,
        )

    def reset_sprite_cache_stats(self) -> None:
        """
        Reset sprite cache hit/miss statistics.
        """

        self._sprite_cache_hits = 0
        self._sprite_cache_misses = 0

    # ------------------------------------------------------------------
    # Screen Space
    # ------------------------------------------------------------------

    def rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: Color = (255, 255, 255),
        *,
        filled: bool = True,
        thickness: int = 1,
        border_radius: int = 0,
    ) -> None:
        ThreadContext.assert_main_thread(
            "Renderer.rectangle"
        )

        rect = pygame.Rect(
            round(x),
            round(y),
            round(width),
            round(height),
        )

        pygame.draw.rect(
            self.surface,
            color,
            rect,
            0 if filled else thickness,
            border_radius,
        )

    def circle(
        self,
        x: float,
        y: float,
        radius: float,
        color: Color = (255, 255, 255),
        *,
        filled: bool = True,
        thickness: int = 1,
    ) -> None:
        ThreadContext.assert_main_thread(
            "Renderer.circle"
        )

        pygame.draw.circle(
            self.surface,
            color,
            (
                round(x),
                round(y),
            ),
            max(0, round(radius)),
            0 if filled else thickness,
        )

    def line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: Color = (255, 255, 255),
        *,
        width: int = 1,
    ) -> None:
        ThreadContext.assert_main_thread(
            "Renderer.line"
        )

        pygame.draw.line(
            self.surface,
            color,
            (
                round(start[0]),
                round(start[1]),
            ),
            (
                round(end[0]),
                round(end[1]),
            ),
            width,
        )

    def polygon(
        self,
        points: Iterable[tuple[float, float]],
        color: Color = (255, 255, 255),
        *,
        filled: bool = True,
        thickness: int = 1,
    ) -> None:
        ThreadContext.assert_main_thread(
            "Renderer.polygon"
        )

        converted = [
            (
                round(x),
                round(y),
            )
            for x, y in points
        ]

        pygame.draw.polygon(
            self.surface,
            color,
            converted,
            0 if filled else thickness,
        )

    def pixel(
        self,
        x: int,
        y: int,
        color: Color = (255, 255, 255),
    ) -> None:
        ThreadContext.assert_main_thread(
            "Renderer.pixel"
        )

        self.surface.set_at(
            (x, y),
            color,
        )

    # ------------------------------------------------------------------
    # Text
    # ------------------------------------------------------------------

    def _get_font(
        self,
        size: int,
        font: str | None,
        bold: bool,
    ) -> pygame.font.Font:
        cache_key = (
            font,
            size,
            bold,
        )

        cached_font = self._font_cache.get(
            cache_key
        )

        if cached_font is None:
            cached_font = pygame.font.Font(
                font,
                size,
            )

            cached_font.set_bold(
                bold
            )

            self._font_cache[
                cache_key
            ] = cached_font

        return cached_font

    def text(
        self,
        value: str,
        x: float,
        y: float,
        *,
        size: int = 24,
        color: Color = (255, 255, 255),
        font: str | None = None,
        bold: bool = False,
    ) -> None:
        ThreadContext.assert_main_thread(
            "Renderer.text"
        )

        cached_font = self._get_font(
            size,
            font,
            bold,
        )

        surface = cached_font.render(
            value,
            True,
            color,
        )

        self.surface.blit(
            surface,
            (
                round(x),
                round(y),
            ),
        )

    def text_size(
        self,
        value: str,
        *,
        size: int = 24,
        font: str | None = None,
        bold: bool = False,
    ) -> tuple[int, int]:
        ThreadContext.assert_main_thread(
            "Renderer.text_size"
        )

        cached_font = self._get_font(
            size,
            font,
            bold,
        )

        return cached_font.size(
            value
        )

    # ------------------------------------------------------------------
    # Surface
    # ------------------------------------------------------------------

    def blit(
        self,
        surface: pygame.Surface,
        x: float,
        y: float,
    ) -> None:
        ThreadContext.assert_main_thread(
            "Renderer.blit"
        )

        self.surface.blit(
            surface,
            (
                round(x),
                round(y),
            ),
        )

    # ------------------------------------------------------------------
    # Sprite Cache
    # ------------------------------------------------------------------

    def _quantize_rotation(
        self,
        rotation: float,
    ) -> float:
        """
        Convert rotation to a cache-friendly value.

        With the default 1 degree step:

            12.1 -> 12
            12.6 -> 13
            359.8 -> 0

        This prevents continuously changing floating-point rotations
        from creating an unlimited number of cache entries.
        """

        rotation %= 360.0

        step = self._rotation_cache_step

        quantized = (
            round(rotation / step)
            * step
        )

        return quantized % 360.0

    def _sprite_cache_key(
        self,
        texture: pygame.Surface,
        width: int,
        height: int,
        rotation: float,
        flip_x: bool,
        flip_y: bool,
    ) -> tuple:
        """
        Create the cache key for a transformed sprite.

        Position and origin are intentionally NOT part of the key.
        """

        return (
            id(texture),
            width,
            height,
            self._quantize_rotation(rotation),
            bool(flip_x),
            bool(flip_y),
        )

    def _get_cached_sprite(
        self,
        texture: pygame.Surface,
        width: int,
        height: int,
        rotation: float,
        flip_x: bool,
        flip_y: bool,
    ) -> pygame.Surface:
        """
        Get a transformed sprite from the LRU cache.

        If the transformation does not exist yet, it is generated,
        inserted into the cache and returned.

        Pygame Surface operations remain main-thread-only.
        """

        ThreadContext.assert_main_thread(
            "Renderer._get_cached_sprite"
        )

        cache_key = self._sprite_cache_key(
            texture,
            width,
            height,
            rotation,
            flip_x,
            flip_y,
        )

        cached = self._sprite_cache.get(
            cache_key
        )

        if cached is not None:
            self._sprite_cache_hits += 1

            self._sprite_cache.move_to_end(
                cache_key
            )

            return cached

        self._sprite_cache_misses += 1

        source = texture

        # --------------------------------------------------------------
        # Scale
        # --------------------------------------------------------------

        if (
            source.get_width() != width
            or source.get_height() != height
        ):
            source = pygame.transform.smoothscale(
                source,
                (
                    width,
                    height,
                ),
            )

        # --------------------------------------------------------------
        # Flip
        # --------------------------------------------------------------

        if flip_x or flip_y:
            source = pygame.transform.flip(
                source,
                flip_x,
                flip_y,
            )

        # --------------------------------------------------------------
        # Rotation
        # --------------------------------------------------------------

        cached_rotation = self._quantize_rotation(
            rotation
        )

        if cached_rotation != 0.0:
            source = pygame.transform.rotate(
                source,
                cached_rotation,
            )

        # --------------------------------------------------------------
        # Insert into LRU cache
        # --------------------------------------------------------------

        self._sprite_cache[
            cache_key
        ] = source

        self._sprite_cache.move_to_end(
            cache_key
        )

        while (
            len(self._sprite_cache)
            > self._sprite_cache_capacity
        ):
            self._sprite_cache.popitem(
                last=False
            )

        return source

    def clear_sprite_cache(self) -> None:
        """
        Clear all cached transformed sprites.
        """

        ThreadContext.assert_main_thread(
            "Renderer.clear_sprite_cache"
        )

        self._sprite_cache.clear()

    # ------------------------------------------------------------------
    # Sprites
    # ------------------------------------------------------------------

    def sprite(
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
    ) -> None:
        """
        Draw a texture in screen space.

        x/y represent the sprite origin.

        By default:

            origin=(0.5, 0.5)

        means the sprite is centered on x/y.

        Transformations are cached automatically.
        """

        ThreadContext.assert_main_thread(
            "Renderer.sprite"
        )

        if not isinstance(texture, pygame.Surface):
            raise TypeError(
                "texture must be a pygame.Surface."
            )

        if len(origin) != 2:
            raise ValueError(
                "origin must contain exactly two values."
            )

        if scale <= 0:
            return

        # --------------------------------------------------------------
        # Size
        # --------------------------------------------------------------

        if width is None:
            width = texture.get_width()

        if height is None:
            height = texture.get_height()

        width = max(
            1,
            round(width * scale),
        )

        height = max(
            1,
            round(height * scale),
        )

        # --------------------------------------------------------------
        # Transform Cache
        # --------------------------------------------------------------

        source = self._get_cached_sprite(
            texture,
            width,
            height,
            rotation,
            flip_x,
            flip_y,
        )

        # --------------------------------------------------------------
        # Alpha
        # --------------------------------------------------------------

        if alpha is not None:
            alpha = max(
                0,
                min(255, int(alpha)),
            )

            source = source.copy()
            source.set_alpha(alpha)

        # --------------------------------------------------------------
        # Origin
        # --------------------------------------------------------------

        origin_x = (
            source.get_width()
            * origin[0]
        )

        origin_y = (
            source.get_height()
            * origin[1]
        )

        destination = (
            round(x - origin_x),
            round(y - origin_y),
        )

        self.surface.blit(
            source,
            destination,
        )

    # ------------------------------------------------------------------
    # World Sprite
    # ------------------------------------------------------------------

    def world_sprite(
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
    ) -> None:
        """
        Draw a texture in world space using the active camera.

        World coordinates are converted to screen coordinates and
        camera zoom is applied to the sprite size.
        """

        ThreadContext.assert_main_thread(
            "Renderer.world_sprite"
        )

        if not isinstance(texture, pygame.Surface):
            raise TypeError(
                "texture must be a pygame.Surface."
            )

        screen_x, screen_y = self.world_to_screen(
            x,
            y,
        )

        zoom = self.camera.zoom

        if width is None:
            width = texture.get_width()

        if height is None:
            height = texture.get_height()

        screen_width = max(
            1,
            round(
                width
                * scale
                * zoom
            ),
        )

        screen_height = max(
            1,
            round(
                height
                * scale
                * zoom
            ),
        )

        self.sprite(
            texture,
            screen_x,
            screen_y,
            width=screen_width,
            height=screen_height,
            rotation=rotation,
            origin=origin,
            flip_x=flip_x,
            flip_y=flip_y,
            alpha=alpha,
        )

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def clear(
        self,
        color: Color | None = None,
    ) -> None:
        ThreadContext.assert_main_thread(
            "Renderer.clear"
        )

        if color is None:
            color = self._clear_color

        self.surface.fill(
            color
        )

    # ------------------------------------------------------------------
    # Camera / World Space
    # ------------------------------------------------------------------

    def world_to_screen(
        self,
        x: float,
        y: float,
    ) -> tuple[float, float]:
        """
        Convert world coordinates to screen coordinates.
        """

        return self.camera.world_to_screen(
            x,
            y,
            self.width,
            self.height,
        )

    def screen_to_world(
        self,
        x: float,
        y: float,
    ) -> tuple[float, float]:
        """
        Convert screen coordinates to world coordinates.
        """

        return self.camera.screen_to_world(
            x,
            y,
            self.width,
            self.height,
        )

    def world_rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: Color = (255, 255, 255),
        *,
        filled: bool = True,
        thickness: int = 1,
        border_radius: int = 0,
    ) -> None:
        """
        Draw a rectangle in world coordinates.
        """

        ThreadContext.assert_main_thread(
            "Renderer.world_rectangle"
        )

        screen_x, screen_y = (
            self.world_to_screen(
                x,
                y,
            )
        )

        screen_width = (
            width * self.camera.zoom
        )

        screen_height = (
            height * self.camera.zoom
        )

        screen_border_radius = max(
            0,
            round(
                border_radius
                * self.camera.zoom
            ),
        )

        screen_thickness = max(
            1,
            round(
                thickness
                * self.camera.zoom
            ),
        )

        self.rectangle(
            screen_x,
            screen_y,
            screen_width,
            screen_height,
            color=color,
            filled=filled,
            thickness=screen_thickness,
            border_radius=screen_border_radius,
        )

    def world_circle(
        self,
        x: float,
        y: float,
        radius: float,
        color: Color = (255, 255, 255),
        *,
        filled: bool = True,
        thickness: int = 1,
    ) -> None:
        """
        Draw a circle in world coordinates.
        """

        ThreadContext.assert_main_thread(
            "Renderer.world_circle"
        )

        screen_x, screen_y = (
            self.world_to_screen(
                x,
                y,
            )
        )

        screen_radius = (
            radius * self.camera.zoom
        )

        screen_thickness = max(
            1,
            round(
                thickness
                * self.camera.zoom
            ),
        )

        self.circle(
            screen_x,
            screen_y,
            screen_radius,
            color=color,
            filled=filled,
            thickness=screen_thickness,
        )

    def world_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: Color = (255, 255, 255),
        *,
        width: int = 1,
    ) -> None:
        """
        Draw a line in world coordinates.
        """

        ThreadContext.assert_main_thread(
            "Renderer.world_line"
        )

        start_screen = (
            self.world_to_screen(
                start[0],
                start[1],
            )
        )

        end_screen = (
            self.world_to_screen(
                end[0],
                end[1],
            )
        )

        screen_width = max(
            1,
            round(
                width
                * self.camera.zoom
            ),
        )

        self.line(
            start_screen,
            end_screen,
            color=color,
            width=screen_width,
        )

    def world_polygon(
        self,
        points: Iterable[tuple[float, float]],
        color: Color = (255, 255, 255),
        *,
        filled: bool = True,
        thickness: int = 1,
    ) -> None:
        """
        Draw a polygon in world coordinates.
        """

        ThreadContext.assert_main_thread(
            "Renderer.world_polygon"
        )

        screen_points = [
            self.world_to_screen(
                x,
                y,
            )
            for x, y in points
        ]

        screen_thickness = max(
            1,
            round(
                thickness
                * self.camera.zoom
            ),
        )

        self.polygon(
            screen_points,
            color=color,
            filled=filled,
            thickness=screen_thickness,
        )

    # ------------------------------------------------------------------
    # Resize
    # ------------------------------------------------------------------

    def resize(self) -> None:
        ThreadContext.assert_main_thread(
            "Renderer.resize"
        )

        self.surface = self.window.surface

    # ------------------------------------------------------------------
    # Font Cache
    # ------------------------------------------------------------------

    def clear_font_cache(self) -> None:
        self._font_cache.clear()