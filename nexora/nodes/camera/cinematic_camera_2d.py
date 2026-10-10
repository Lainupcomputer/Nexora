from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Callable,
)

from nexora.nodes.camera.camera_2d import Camera2D


if TYPE_CHECKING:
    from nexora.rendering.renderer import Renderer


from nexora.nodes.camera.cinematic_queue import CinematicQueueMixin
from nexora.nodes.camera.cinematic_sequence import CinematicSequenceMixin
from nexora.nodes.camera.cinematic_step import CameraStep


# ==============================================================
# CinematicCamera2D
# ==============================================================


class CinematicCamera2D(CinematicQueueMixin, CinematicSequenceMixin, Camera2D):
    """
    Scriptable cinematic 2D camera.

    CinematicCamera2D allows camera movements and visual effects
    to be queued and played as a sequence.

    Supported sequence steps:

        Transform:
            - move_to
            - move_to_node
            - zoom_to
            - move_zoom_to
            - transform_to

        Timing:
            - wait

        Screen effects:
            - queue_fade_out
            - queue_fade_in
            - queue_flash
            - queue_letterbox
            - queue_clear_letterbox

        Camera effects:
            - queue_shake
            - queue_trauma
            - queue_punch

    Example:

        camera \
            .queue_letterbox(
                90.0,
                duration=0.5,
            ) \
            .move_to(
                800.0,
                500.0,
                duration=2.0,
            ) \
            .wait(
                0.5
            ) \
            .queue_fade_out(
                duration=0.75,
            ) \
            .wait(
                0.25
            ) \
            .queue_fade_in(
                duration=0.75,
            ) \
            .queue_clear_letterbox(
                duration=0.5,
            ) \
            .play()
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
            renderer,
        )

        # ======================================================
        # Cinematic transform state
        # ======================================================

        self._x: float = float(
            self.camera.x
        )

        self._y: float = float(
            self.camera.y
        )

        self._zoom: float = float(
            self.camera.zoom
        )

        # ======================================================
        # Sequence
        # ======================================================

        self._sequence: list[
            CameraStep
        ] = []

        self._current_step: int = 0

        self.playing: bool = False

        self.loop: bool = False

        # ======================================================
        # Callbacks
        # ======================================================

        self.on_step_finished: (
            Callable[[int], None]
            | None
        ) = None

        self.on_sequence_finished: (
            Callable[[], None]
            | None
        ) = None

    # ==========================================================
    # State
    # ==========================================================

    @property
    def position(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            self._x,
            self._y,
        )

    @property
    def sequence_length(
        self,
    ) -> int:
        return len(
            self._sequence
        )

    @property
    def current_step(
        self,
    ) -> int:
        return self._current_step

    @property
    def finished(
        self,
    ) -> bool:
        return (
            bool(
                self._sequence
            )
            and not self.playing
            and self._current_step
            >= len(
                self._sequence
            )
        )

    # ==========================================================
    # Position
    # ==========================================================

    def set_position(
        self,
        x: float,
        y: float,
    ) -> None:
        self._x = float(
            x
        )

        self._y = float(
            y
        )

        Camera2D.set_position(
            self,
            self._x,
            self._y,
        )

    # ==========================================================
    # Zoom
    # ==========================================================

    def set_zoom(
        self,
        zoom: float,
    ) -> None:
        self._zoom = float(
            zoom
        )

        Camera2D.set_zoom(
            self,
            self._zoom,
        )

    # ==========================================================
    # Sequence management
    # ==========================================================

    def clear_sequence(
        self,
    ) -> CinematicCamera2D:
        """
        Remove all queued cinematic steps.
        """

        self._sequence.clear()

        self._current_step = 0

        self.playing = False

        return self

    def play(
        self,
        *,
        restart: bool = False,
    ) -> CinematicCamera2D:
        """
        Start playing the cinematic sequence.
        """

        if not self._sequence:
            return self

        if restart:
            return self.restart()

        if (
            self._current_step
            >= len(
                self._sequence
            )
        ):
            self._current_step = 0

            self._reset_steps()

        self.playing = True

        return self

    def pause(
        self,
    ) -> CinematicCamera2D:
        """
        Pause the cinematic sequence.
        """

        self.playing = False

        return self

    def resume(
        self,
    ) -> CinematicCamera2D:
        """
        Resume a paused cinematic sequence.
        """

        if (
            self._sequence
            and self._current_step
            < len(
                self._sequence
            )
        ):
            self.playing = True

        return self

    def stop(
        self,
    ) -> CinematicCamera2D:
        """
        Stop and reset sequence playback.
        """

        self.playing = False

        self._current_step = 0

        self._reset_steps()

        return self

    def restart(
        self,
    ) -> CinematicCamera2D:
        """
        Restart the cinematic from the first step.
        """

        self._current_step = 0

        self._reset_steps()

        self.playing = bool(
            self._sequence
        )

        return self

    def _reset_steps(
        self,
    ) -> None:
        for step in self._sequence:
            step.elapsed = 0.0
            step.started = False

















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
        # Camera2D effects first.
        #
        # This is important because cinematic effect steps
        # inspect is_fading/is_flashing/etc.
        # ------------------------------------------------------

        Camera2D.update(
            self,
            delta_time,
        )

        # ------------------------------------------------------
        # Cinematic sequence
        # ------------------------------------------------------

        self._update_sequence(
            delta_time
        )
