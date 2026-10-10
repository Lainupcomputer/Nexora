from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Callable,
)

from nexora.nodes.node import Node
from nexora.nodes.camera.easing import ease_value
from nexora.nodes.camera.interpolation import lerp_value
from nexora.nodes.camera.transform import CameraTransformMixin
from nexora.nodes.camera.motion_effects import CameraMotionEffectsMixin
from nexora.nodes.camera.overlays import CameraOverlayMixin


if TYPE_CHECKING:
    from nexora.rendering.renderer import Renderer


Color = tuple[
    float,
    float,
    float,
]


class Camera2D(
    CameraTransformMixin,
    CameraMotionEffectsMixin,
    CameraOverlayMixin,
    Node,
):
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
        return lerp_value(
            start,
            end,
            progress,
        )

    @staticmethod
    def _ease(
        progress: float,
        easing: str,
    ) -> float:
        return ease_value(
            progress,
            easing,
        )

    # ==========================================================
    # Position
    # ==========================================================



    # ==========================================================
    # Zoom
    # ==========================================================





    # ==========================================================
    # Bounds
    # ==========================================================




    # ==========================================================
    # Dead zone
    # ==========================================================



    # ==========================================================
    # Normal shake
    # ==========================================================



    # ==========================================================
    # Trauma shake
    # ==========================================================





    # ==========================================================
    # Camera punch
    # ==========================================================




    # ==========================================================
    # Fade
    # ==========================================================








    # ==========================================================
    # Flash
    # ==========================================================






    # ==========================================================
    # Letterbox
    # ==========================================================






    # ==========================================================
    # Reset effects
    # ==========================================================


    # ==========================================================
    # Coordinate conversion
    # ==========================================================



    # ==========================================================
    # Screen overlay helpers
    # ==========================================================


    # ==========================================================
    # Render effects
    # ==========================================================




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
