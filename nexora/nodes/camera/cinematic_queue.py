from __future__ import annotations

from typing import TYPE_CHECKING

from nexora.nodes.camera.cinematic_step import _CameraStep
from nexora.nodes.camera.easing import EASING_FUNCTIONS as _EASING_FUNCTIONS

if TYPE_CHECKING:
    from nexora.nodes.camera.cinematic_camera_2d import CinematicCamera2D
    from nexora.nodes.node import Node

Color = tuple[float, float, float]


class CinematicQueueMixin:
    """Internal queue-building API for CinematicCamera2D."""

    def move_to(
        self,
        x: float,
        y: float,
        *,
        duration: float = 1.0,
        easing: str = "ease_in_out",
    ) -> CinematicCamera2D:
        """
        Queue movement to a world position.
        """

        self._validate_duration(
            duration
        )

        self._validate_easing(
            easing
        )

        self._sequence.append(
            _CameraStep(
                kind="move",
                x=float(
                    x
                ),
                y=float(
                    y
                ),
                duration=float(
                    duration
                ),
                easing=easing,
            )
        )

        return self

    def move_to_node(
        self,
        target: Node,
        *,
        duration: float = 1.0,
        easing: str = "ease_in_out",
    ) -> CinematicCamera2D:
        """
        Queue movement toward a node.

        The target position is resolved continuously while
        moving, allowing the target itself to move.
        """

        self._validate_duration(
            duration
        )

        self._validate_easing(
            easing
        )

        self._sequence.append(
            _CameraStep(
                kind="move_target",
                target=target,
                duration=float(
                    duration
                ),
                easing=easing,
            )
        )

        return self

    def zoom_to(
        self,
        zoom: float,
        *,
        duration: float = 1.0,
        easing: str = "ease_in_out",
    ) -> CinematicCamera2D:
        """
        Queue a cinematic zoom transition.

        This intentionally overrides Camera2D.zoom_to().

        Camera2D.zoom_to():
            immediately starts renderer camera zoom.

        CinematicCamera2D.zoom_to():
            queues zoom as part of the cinematic sequence.
        """

        self._validate_duration(
            duration
        )

        self._validate_easing(
            easing
        )

        self._sequence.append(
            _CameraStep(
                kind="zoom",
                zoom=float(
                    zoom
                ),
                duration=float(
                    duration
                ),
                easing=easing,
            )
        )

        return self

    def move_zoom_to(
        self,
        x: float,
        y: float,
        *,
        zoom: float,
        duration: float = 1.0,
        easing: str = "ease_in_out",
    ) -> CinematicCamera2D:
        """
        Queue simultaneous movement and zoom.
        """

        self._validate_duration(
            duration
        )

        self._validate_easing(
            easing
        )

        self._sequence.append(
            _CameraStep(
                kind="move_zoom",
                x=float(
                    x
                ),
                y=float(
                    y
                ),
                zoom=float(
                    zoom
                ),
                duration=float(
                    duration
                ),
                easing=easing,
            )
        )

        return self

    def transform_to(
        self,
        x: float,
        y: float,
        *,
        zoom: float | None = None,
        duration: float = 1.0,
        easing: str = "ease_in_out",
    ) -> CinematicCamera2D:
        """
        Queue a complete cinematic transform.

        Currently supports:

            - position
            - zoom

        Rotation can later be added once renderer camera
        rotation exists.
        """

        self._validate_duration(
            duration
        )

        self._validate_easing(
            easing
        )

        self._sequence.append(
            _CameraStep(
                kind="transform",
                x=float(
                    x
                ),
                y=float(
                    y
                ),
                zoom=(
                    None
                    if zoom is None
                    else float(
                        zoom
                    )
                ),
                duration=float(
                    duration
                ),
                easing=easing,
            )
        )

        return self

    def wait(
        self,
        duration: float,
    ) -> CinematicCamera2D:
        """
        Queue a delay.
        """

        self._validate_duration(
            duration
        )

        self._sequence.append(
            _CameraStep(
                kind="wait",
                duration=float(
                    duration
                ),
                easing="linear",
            )
        )

        return self

    def queue_fade_out(
        self,
        duration: float = 0.5,
        *,
        color: Color = (
            0.0,
            0.0,
            0.0,
        ),
        easing: str = "ease_in_out",
    ) -> CinematicCamera2D:
        """
        Queue a fade to a solid color.

        The next sequence step starts only after the fade
        has completed.
        """

        self._validate_duration(
            duration
        )

        self._validate_easing(
            easing
        )

        self._sequence.append(
            _CameraStep(
                kind="fade_out",
                duration=float(
                    duration
                ),
                color=(
                    float(
                        color[0]
                    ),
                    float(
                        color[1]
                    ),
                    float(
                        color[2]
                    ),
                ),
                easing=easing,
            )
        )

        return self

    def queue_fade_in(
        self,
        duration: float = 0.5,
        *,
        easing: str = "ease_in_out",
    ) -> CinematicCamera2D:
        """
        Queue a fade back into the game.
        """

        self._validate_duration(
            duration
        )

        self._validate_easing(
            easing
        )

        self._sequence.append(
            _CameraStep(
                kind="fade_in",
                duration=float(
                    duration
                ),
                easing=easing,
            )
        )

        return self

    def queue_flash(
        self,
        *,
        color: Color = (
            1.0,
            1.0,
            1.0,
        ),
        alpha: float = 1.0,
        duration: float = 0.15,
    ) -> CinematicCamera2D:
        """
        Queue a screen flash.

        The cinematic waits for the flash to complete before
        advancing.
        """

        self._validate_duration(
            duration
        )

        self._sequence.append(
            _CameraStep(
                kind="flash",
                duration=float(
                    duration
                ),
                color=(
                    float(
                        color[0]
                    ),
                    float(
                        color[1]
                    ),
                    float(
                        color[2]
                    ),
                ),
                alpha=float(
                    alpha
                ),
                easing="linear",
            )
        )

        return self

    def queue_letterbox(
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
    ) -> CinematicCamera2D:
        """
        Queue cinematic letterbox bars.
        """

        self._validate_duration(
            duration
        )

        self._validate_easing(
            easing
        )

        self._sequence.append(
            _CameraStep(
                kind="letterbox",
                duration=float(
                    duration
                ),
                size=max(
                    0.0,
                    float(
                        size
                    ),
                ),
                color=(
                    float(
                        color[0]
                    ),
                    float(
                        color[1]
                    ),
                    float(
                        color[2]
                    ),
                ),
                easing=easing,
            )
        )

        return self

    def queue_clear_letterbox(
        self,
        *,
        duration: float = 0.35,
        easing: str = "ease_in_out",
    ) -> CinematicCamera2D:
        """
        Queue removal of cinematic letterbox bars.
        """

        self._validate_duration(
            duration
        )

        self._validate_easing(
            easing
        )

        self._sequence.append(
            _CameraStep(
                kind="clear_letterbox",
                duration=float(
                    duration
                ),
                easing=easing,
            )
        )

        return self

    def queue_shake(
        self,
        intensity: float,
        duration: float,
    ) -> CinematicCamera2D:
        """
        Queue traditional timed camera shake.
        """

        self._validate_duration(
            duration
        )

        self._sequence.append(
            _CameraStep(
                kind="shake",
                duration=float(
                    duration
                ),
                alpha=float(
                    intensity
                ),
                easing="linear",
            )
        )

        return self

    def queue_trauma(
        self,
        amount: float,
        *,
        wait: float = 0.0,
    ) -> CinematicCamera2D:
        """
        Queue trauma.

        The trauma itself is added immediately when this step
        starts.

        wait determines how long the sequence waits before
        continuing to the next step.
        """

        self._validate_duration(
            wait
        )

        self._sequence.append(
            _CameraStep(
                kind="trauma",
                duration=float(
                    wait
                ),
                alpha=float(
                    amount
                ),
                easing="linear",
            )
        )

        return self

    def queue_punch(
        self,
        x: float,
        y: float,
        *,
        duration: float = 0.15,
    ) -> CinematicCamera2D:
        """
        Queue a directional camera punch.
        """

        self._validate_duration(
            duration
        )

        self._sequence.append(
            _CameraStep(
                kind="punch",
                x=float(
                    x
                ),
                y=float(
                    y
                ),
                duration=float(
                    duration
                ),
                easing="linear",
            )
        )

        return self

    @staticmethod
    def _validate_duration(
        duration: float,
    ) -> None:
        if float(
            duration
        ) < 0.0:
            raise ValueError(
                "Camera step duration cannot be negative."
            )

    @staticmethod
    def _validate_easing(
        easing: str,
    ) -> None:
        if easing not in _EASING_FUNCTIONS:
            available = ", ".join(
                _EASING_FUNCTIONS
            )

            raise ValueError(
                f"Unknown camera easing: {easing!r}. "
                f"Available: {available}"
            )
