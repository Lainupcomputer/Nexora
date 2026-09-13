from __future__ import annotations

import random

from typing import (
    TYPE_CHECKING,
    Callable,
)

from nexora.nodes.node import Node


if TYPE_CHECKING:
    from nexora.rendering.renderer import Renderer


Color = tuple[
    float,
    float,
    float,
]


class Camera2D(Node):
    """
    Base class for all 2D camera nodes.

    Camera2D wraps and controls the renderer camera while
    providing common camera behaviour and visual effects.

    Specialized implementations may include:

        - FollowCamera2D
        - FreeCamera2D
        - CinematicCamera2D
        - FixedCamera2D

    Built-in effects:

        - normal shake
        - trauma shake
        - camera punch
        - fade
        - flash
        - letterbox
    """

    def __init__(
        self,
        name: str,
        world,
        renderer: Renderer,
    ) -> None:
        super().__init__(
            name,
            world,
        )

        self.renderer = renderer

        self.active: bool = True

        self.clamp_to_bounds: bool = True

        # ======================================================
        # Fade
        # ======================================================

        self.fade_alpha: float = 0.0

        self.fade_color: Color = (
            0.0,
            0.0,
            0.0,
        )

        self._fade_start_alpha: float = 0.0
        self._fade_target_alpha: float = 0.0

        self._fade_duration: float = 0.0
        self._fade_elapsed: float = 0.0

        self._fade_active: bool = False

        self._fade_easing: str = "ease_in_out"

        self._fade_callback: (
            Callable[[], None] | None
        ) = None

        # ======================================================
        # Flash
        # ======================================================

        self.flash_alpha: float = 0.0

        self.flash_color: Color = (
            1.0,
            1.0,
            1.0,
        )

        self._flash_start_alpha: float = 0.0

        self._flash_duration: float = 0.0
        self._flash_elapsed: float = 0.0

        self._flash_active: bool = False

        # ======================================================
        # Trauma shake
        # ======================================================

        self.trauma: float = 0.0

        self.trauma_decay: float = 1.5

        self.trauma_strength: float = 25.0

        self.trauma_power: float = 2.0

        # ======================================================
        # Camera punch
        # ======================================================

        self._punch_x: float = 0.0
        self._punch_y: float = 0.0

        self._punch_duration: float = 0.0
        self._punch_elapsed: float = 0.0

        self._punch_active: bool = False

        # ======================================================
        # Letterbox
        # ======================================================

        self.letterbox_size: float = 0.0

        self.letterbox_color: Color = (
            0.0,
            0.0,
            0.0,
        )

        self._letterbox_start_size: float = 0.0
        self._letterbox_target_size: float = 0.0

        self._letterbox_duration: float = 0.0
        self._letterbox_elapsed: float = 0.0

        self._letterbox_active: bool = False

        self._letterbox_easing: str = "ease_in_out"

    # ==========================================================
    # Render camera
    # ==========================================================

    @property
    def camera(self):
        """
        Return the underlying renderer camera.
        """

        return self.renderer.camera

    # ==========================================================
    # Utility
    # ==========================================================

    @staticmethod
    def _clamp01(
        value: float,
    ) -> float:
        return max(
            0.0,
            min(
                1.0,
                float(value),
            ),
        )

    @staticmethod
    def _lerp(
        start: float,
        end: float,
        progress: float,
    ) -> float:
        return (
            start
            + (
                end
                - start
            )
            * progress
        )

    @staticmethod
    def _ease(
        progress: float,
        easing: str,
    ) -> float:
        progress = max(
            0.0,
            min(
                1.0,
                progress,
            ),
        )

        if easing == "linear":
            return progress

        if easing == "ease_in":
            return (
                progress
                * progress
            )

        if easing == "ease_out":
            inverse = (
                1.0
                - progress
            )

            return (
                1.0
                - inverse
                * inverse
            )

        if easing == "ease_in_out":
            if progress < 0.5:
                return (
                    2.0
                    * progress
                    * progress
                )

            return (
                1.0
                - (
                    (
                        -2.0
                        * progress
                        + 2.0
                    )
                    ** 2
                )
                / 2.0
            )

        raise ValueError(
            f"Unknown easing: {easing!r}"
        )

    # ==========================================================
    # Position
    # ==========================================================

    def set_position(
        self,
        x: float,
        y: float,
    ) -> None:
        """
        Set camera world position.
        """

        self.camera.set_position(
            float(x),
            float(y),
        )

    def move(
        self,
        x: float,
        y: float,
    ) -> None:
        """
        Move camera relative to its current position.
        """

        self.camera.move(
            float(x),
            float(y),
        )

    # ==========================================================
    # Zoom
    # ==========================================================

    @property
    def zoom(self) -> float:
        return self.camera.zoom

    @zoom.setter
    def zoom(
        self,
        value: float,
    ) -> None:
        self.camera.set_zoom(
            float(value)
        )

    def set_zoom(
        self,
        zoom: float,
    ) -> None:
        self.camera.set_zoom(
            float(zoom)
        )

    def zoom_to(
        self,
        zoom: float,
    ) -> None:
        """
        Smoothly transition to a zoom level.
        """

        self.camera.zoom_to(
            float(zoom)
        )

    # ==========================================================
    # Bounds
    # ==========================================================

    def set_bounds(
        self,
        min_x: float | None = None,
        max_x: float | None = None,
        min_y: float | None = None,
        max_y: float | None = None,
    ) -> None:
        self.camera.set_bounds(
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
        )

    def clear_bounds(
        self,
    ) -> None:
        self.camera.clear_bounds()

    def clamp(
        self,
    ) -> None:
        if not self.clamp_to_bounds:
            return

        self.camera.clamp(
            self.renderer.width,
            self.renderer.height,
        )

    # ==========================================================
    # Dead zone
    # ==========================================================

    def set_dead_zone(
        self,
        width: float,
        height: float,
    ) -> None:
        """
        Set camera follow dead zone.
        """

        self.camera.set_dead_zone(
            float(width),
            float(height),
        )

    def clear_dead_zone(
        self,
    ) -> None:
        """
        Disable camera dead zone.
        """

        self.camera.clear_dead_zone()

    # ==========================================================
    # Normal shake
    # ==========================================================

    def shake(
        self,
        intensity: float,
        duration: float,
    ) -> None:
        """
        Start a traditional timed screen shake.
        """

        self.camera.shake(
            strength=float(
                intensity
            ),
            duration=float(
                duration
            ),
        )

    def stop_shake(
        self,
    ) -> None:
        """
        Stop traditional screen shake.
        """

        self.camera.stop_shake()

    # ==========================================================
    # Trauma shake
    # ==========================================================

    def add_trauma(
        self,
        amount: float,
    ) -> None:
        """
        Add trauma to the camera.

        Trauma is clamped between 0 and 1.
        """

        self.trauma = self._clamp01(
            self.trauma
            + float(amount)
        )

    def set_trauma(
        self,
        amount: float,
    ) -> None:
        self.trauma = self._clamp01(
            amount
        )

    def clear_trauma(
        self,
    ) -> None:
        self.trauma = 0.0

    def _update_trauma(
        self,
        delta_time: float,
    ) -> None:
        if self.trauma <= 0.0:
            return

        amount = (
            self.trauma
            ** self.trauma_power
        )

        strength = (
            self.trauma_strength
            * amount
        )

        self.camera.shake_x += (
            random.uniform(
                -1.0,
                1.0,
            )
            * strength
        )

        self.camera.shake_y += (
            random.uniform(
                -1.0,
                1.0,
            )
            * strength
        )

        self.trauma = max(
            0.0,
            self.trauma
            - self.trauma_decay
            * delta_time,
        )

    # ==========================================================
    # Camera punch
    # ==========================================================

    def punch(
        self,
        x: float,
        y: float,
        *,
        duration: float = 0.15,
    ) -> None:
        """
        Apply a directional camera kick.

        Useful for weapon recoil, impacts or explosions.
        """

        duration = float(
            duration
        )

        if duration <= 0.0:
            return

        self._punch_x = float(
            x
        )

        self._punch_y = float(
            y
        )

        self._punch_duration = duration

        self._punch_elapsed = 0.0

        self._punch_active = True

    def stop_punch(
        self,
    ) -> None:
        self._punch_active = False

        self._punch_x = 0.0
        self._punch_y = 0.0

        self._punch_duration = 0.0
        self._punch_elapsed = 0.0

    def _update_punch(
        self,
        delta_time: float,
    ) -> None:
        if not self._punch_active:
            return

        self._punch_elapsed += (
            delta_time
        )

        progress = min(
            self._punch_elapsed
            / self._punch_duration,
            1.0,
        )

        decay = (
            1.0
            - self._ease(
                progress,
                "ease_out",
            )
        )

        self.camera.shake_x += (
            self._punch_x
            * decay
        )

        self.camera.shake_y += (
            self._punch_y
            * decay
        )

        if progress >= 1.0:
            self.stop_punch()

    # ==========================================================
    # Fade
    # ==========================================================

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

    # ==========================================================
    # Flash
    # ==========================================================

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

    # ==========================================================
    # Letterbox
    # ==========================================================

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

    # ==========================================================
    # Reset effects
    # ==========================================================

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

    # ==========================================================
    # Coordinate conversion
    # ==========================================================

    def world_to_screen(
        self,
        x: float,
        y: float,
    ) -> tuple[float, float]:
        return self.camera.world_to_screen(
            x,
            y,
            self.renderer.width,
            self.renderer.height,
        )

    def screen_to_world(
        self,
        x: float,
        y: float,
    ) -> tuple[float, float]:
        return self.camera.screen_to_world(
            x,
            y,
            self.renderer.width,
            self.renderer.height,
        )

    # ==========================================================
    # Screen overlay helpers
    # ==========================================================

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

    # ==========================================================
    # Render effects
    # ==========================================================

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

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        if not self.active:
            return

        # ------------------------------------------------------
        # Base camera systems
        # ------------------------------------------------------

        self.camera.update_zoom(
            delta_time
        )

        self.camera.update_shake(
            delta_time
        )

        # ------------------------------------------------------
        # Additive movement effects
        # ------------------------------------------------------

        self._update_trauma(
            delta_time
        )

        self._update_punch(
            delta_time
        )

        # ------------------------------------------------------
        # Screen effects
        # ------------------------------------------------------

        self._update_fade(
            delta_time
        )

        self._update_flash(
            delta_time
        )

        self._update_letterbox(
            delta_time
        )

        # ------------------------------------------------------
        # Bounds
        # ------------------------------------------------------

        self.clamp()

    def render(
        self,
        renderer,
        interpolation: float,
    ) -> None:
        if not self.active:
            return

        # ------------------------------------------------------
        # Camera overlays
        # ------------------------------------------------------

        self._render_letterbox(
            renderer
        )

        self._render_fade(
            renderer
        )

        self._render_flash(
            renderer
        )