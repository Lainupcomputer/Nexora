from __future__ import annotations

from typing import Iterable

import pygame

from nexora.rendering.camera import Camera
from nexora.threading.context import ThreadContext


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
        text()
        blit()

    World Space:
        world_rectangle()
        world_circle()
        world_line()
        world_to_screen()
    """

    def __init__(self, window) -> None:
        self.window = window
        self.surface = window.surface

        self.camera = Camera()

        self._clear_color: Color = (25, 25, 30)

        self._font_cache: dict[
            tuple[str | None, int, bool],
            pygame.font.Font,
        ] = {}

        self._frame_started = False

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

