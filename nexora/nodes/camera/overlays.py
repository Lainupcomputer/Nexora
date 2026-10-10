from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from nexora.rendering.renderer import Renderer

Color = tuple[float, float, float]

class CameraOverlayMixin:

    @property
    def is_fading(
        self,
    ) -> bool:
        return self._fade_active

    def fade_to(
        self,
        alpha: float,
        *,
        duration: float = 0.5,
        color: Color | None = None,
        easing: str = "ease_in_out",
        on_complete: Callable[
            [],
            None,
        ]
        | None = None,
    ) -> None:
        """
        Fade the screen toward an alpha value.

        alpha:
            0 = fully visible
            1 = fully covered
        """

        alpha = self._clamp01(
            alpha
        )

        duration = max(
            0.0,
            float(duration),
        )

        self._ease(
            0.0,
            easing,
        )

        if color is not None:
            self.fade_color = (
                float(
                    color[0]
                ),
                float(
                    color[1]
                ),
                float(
                    color[2]
                ),
            )

        self._fade_start_alpha = (
            self.fade_alpha
        )

        self._fade_target_alpha = (
            alpha
        )

        self._fade_duration = (
            duration
        )

        self._fade_elapsed = 0.0

        self._fade_easing = easing

        self._fade_callback = (
            on_complete
        )

        if duration <= 0.0:
            self.fade_alpha = alpha

            self._fade_active = False

            self._finish_fade()

            return

        self._fade_active = True

    def fade_out(
        self,
        duration: float = 0.5,
        *,
        color: Color = (
            0.0,
            0.0,
            0.0,
        ),
        easing: str = "ease_in_out",
        on_complete: Callable[
            [],
            None,
        ]
        | None = None,
    ) -> None:
        """
        Fade from the game view to a solid color.
        """

        self.fade_to(
            1.0,
            duration=duration,
            color=color,
            easing=easing,
            on_complete=on_complete,
        )

    def fade_in(
        self,
        duration: float = 0.5,
        *,
        easing: str = "ease_in_out",
        on_complete: Callable[
            [],
            None,
        ]
        | None = None,
    ) -> None:
        """
        Fade from the current fade color back into the game.
        """

        self.fade_to(
            0.0,
            duration=duration,
            easing=easing,
            on_complete=on_complete,
        )

    def clear_fade(
        self,
    ) -> None:
        """
        Immediately remove the current fade effect.
        """

        self.fade_alpha = 0.0

        self._fade_start_alpha = 0.0
        self._fade_target_alpha = 0.0

        self._fade_duration = 0.0
        self._fade_elapsed = 0.0

        self._fade_active = False

        self._fade_callback = None

    def _finish_fade(
        self,
    ) -> None:
        callback = (
            self._fade_callback
        )

        self._fade_callback = None

        if callback is not None:
            callback()

    def _update_fade(
        self,
        delta_time: float,
    ) -> None:
        if not self._fade_active:
            return

        self._fade_elapsed += (
            delta_time
        )

        progress = min(
            self._fade_elapsed
            / self._fade_duration,
            1.0,
        )

        eased = self._ease(
            progress,
            self._fade_easing,
        )

        self.fade_alpha = self._lerp(
            self._fade_start_alpha,
            self._fade_target_alpha,
            eased,
        )

        if progress >= 1.0:
            self.fade_alpha = (
                self._fade_target_alpha
            )

            self._fade_active = False

            self._finish_fade()

    @property
    def is_flashing(
        self,
    ) -> bool:
        return self._flash_active

    def flash(
        self,
        *,
        color: Color = (
            1.0,
            1.0,
            1.0,
        ),
        alpha: float = 1.0,
        duration: float = 0.15,
    ) -> None:
        """
        Flash the screen with a color.
        """

        duration = float(
            duration
        )

        if duration <= 0.0:
            return

        self.flash_color = (
            float(
                color[0]
            ),
            float(
                color[1]
            ),
            float(
                color[2]
            ),
        )

        self.flash_alpha = (
            self._clamp01(
                alpha
            )
        )

        self._flash_start_alpha = (
            self.flash_alpha
        )

        self._flash_duration = (
            duration
        )

        self._flash_elapsed = 0.0

        self._flash_active = True

    def stop_flash(
        self,
    ) -> None:
        self.flash_alpha = 0.0

        self._flash_start_alpha = 0.0

        self._flash_duration = 0.0
        self._flash_elapsed = 0.0

        self._flash_active = False

    def clear_flash(
        self,
    ) -> None:
        """
        Immediately remove the current flash effect.
        """

        self.stop_flash()

    def _update_flash(
        self,
        delta_time: float,
    ) -> None:
        if not self._flash_active:
            return

        self._flash_elapsed += (
            delta_time
        )

        progress = min(
            self._flash_elapsed
            / self._flash_duration,
            1.0,
        )

        decay = (
            1.0
            - self._ease(
                progress,
                "ease_out",
            )
        )

        self.flash_alpha = (
            self._flash_start_alpha
            * decay
        )

        if progress >= 1.0:
            self.stop_flash()

    @property
    def has_letterbox(
        self,
    ) -> bool:
        return (
            self.letterbox_size
            > 0.0
        )

    def letterbox(
        self,
        size: float = 80.0,
        *,
        duration: float = 0.35,
        color: Color = (
            0.0,
            0.0,
            0.0,
        ),
        easing: str = "ease_in_out",
    ) -> None:
        """
        Animate cinematic bars onto the screen.

        size is specified in screen pixels.
        """

        size = max(
            0.0,
            float(size),
        )

        duration = max(
            0.0,
            float(duration),
        )

        self._ease(
            0.0,
            easing,
        )

        self.letterbox_color = (
            float(
                color[0]
            ),
            float(
                color[1]
            ),
            float(
                color[2]
            ),
        )

        self._letterbox_start_size = (
            self.letterbox_size
        )

        self._letterbox_target_size = (
            size
        )

        self._letterbox_duration = (
            duration
        )

        self._letterbox_elapsed = 0.0

        self._letterbox_easing = (
            easing
        )

        if duration <= 0.0:
            self.letterbox_size = size

            self._letterbox_active = (
                False
            )

            return

        self._letterbox_active = True

    def clear_letterbox(
        self,
        *,
        duration: float = 0.35,
        easing: str = "ease_in_out",
    ) -> None:
        """
        Animate cinematic bars off the screen.
        """

        self.letterbox(
            0.0,
            duration=duration,
            color=self.letterbox_color,
            easing=easing,
        )

    def reset_letterbox(
        self,
    ) -> None:
        """
        Immediately remove cinematic letterbox bars.
        """

        self.letterbox_size = 0.0

        self._letterbox_start_size = 0.0
        self._letterbox_target_size = 0.0

        self._letterbox_duration = 0.0
        self._letterbox_elapsed = 0.0

        self._letterbox_active = False

    def _update_letterbox(
        self,
        delta_time: float,
    ) -> None:
        if not self._letterbox_active:
            return

        self._letterbox_elapsed += (
            delta_time
        )

        progress = min(
            self._letterbox_elapsed
            / self._letterbox_duration,
            1.0,
        )

        eased = self._ease(
            progress,
            self._letterbox_easing,
        )

        self.letterbox_size = self._lerp(
            self._letterbox_start_size,
            self._letterbox_target_size,
            eased,
        )

        if progress >= 1.0:
            self.letterbox_size = (
                self._letterbox_target_size
            )

            self._letterbox_active = False

    def reset_effects(
        self,
        *,
        reset_fade: bool = True,
        reset_flash: bool = True,
        reset_shake: bool = True,
        reset_trauma: bool = True,
        reset_punch: bool = True,
        reset_letterbox: bool = True,
    ) -> None:
        """
        Reset camera effects.

        Individual effect groups can be preserved by setting
        their corresponding reset flag to False.
        """

        if reset_shake:
            self.stop_shake()

        if reset_trauma:
            self.clear_trauma()

        if reset_punch:
            self.stop_punch()

        if reset_flash:
            self.clear_flash()

        if reset_fade:
            self.clear_fade()

        if reset_letterbox:
            self.reset_letterbox()

    def _draw_screen_rect(
        self,
        renderer: Renderer,
        screen_x: float,
        screen_y: float,
        width: float,
        height: float,
        color: tuple[
            float,
            float,
            float,
            float,
        ],
    ) -> None:
        """
        Draw a rectangle using screen-space coordinates while
        compensating for camera position, zoom and shake.

        This keeps camera effects fixed to the viewport.
        """

        zoom = max(
            self.camera.zoom,
            0.0001,
        )

        viewport_center_x = (
            renderer.width
            * 0.5
        )

        viewport_center_y = (
            renderer.height
            * 0.5
        )

        world_x = (
            self.camera.x
            - self.camera.shake_x
            + (
                screen_x
                - viewport_center_x
            )
            / zoom
        )

        world_y = (
            self.camera.y
            - self.camera.shake_y
            + (
                screen_y
                - viewport_center_y
            )
            / zoom
        )

        renderer.rect(
            world_x,
            world_y,
            width / zoom,
            height / zoom,
            color=color,
            origin=(
                0.5,
                0.5,
            ),
        )

    def _render_letterbox(
        self,
        renderer: Renderer,
    ) -> None:
        size = min(
            self.letterbox_size,
            renderer.height
            * 0.5,
        )

        if size <= 0.0:
            return

        r, g, b = (
            self.letterbox_color
        )

        color = (
            r,
            g,
            b,
            1.0,
        )

        # Top
        self._draw_screen_rect(
            renderer,
            renderer.width
            * 0.5,
            size
            * 0.5,
            renderer.width,
            size,
            color,
        )

        # Bottom
        self._draw_screen_rect(
            renderer,
            renderer.width
            * 0.5,
            renderer.height
            - size
            * 0.5,
            renderer.width,
            size,
            color,
        )

    def _render_fade(
        self,
        renderer: Renderer,
    ) -> None:
        if self.fade_alpha <= 0.0:
            return

        r, g, b = (
            self.fade_color
        )

        self._draw_screen_rect(
            renderer,
            renderer.width
            * 0.5,
            renderer.height
            * 0.5,
            renderer.width,
            renderer.height,
            (
                r,
                g,
                b,
                self.fade_alpha,
            ),
        )

    def _render_flash(
        self,
        renderer: Renderer,
    ) -> None:
        if self.flash_alpha <= 0.0:
            return

        r, g, b = (
            self.flash_color
        )

        self._draw_screen_rect(
            renderer,
            renderer.width
            * 0.5,
            renderer.height
            * 0.5,
            renderer.width,
            renderer.height,
            (
                r,
                g,
                b,
                self.flash_alpha,
            ),
        )
