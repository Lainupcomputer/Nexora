from __future__ import annotations

from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Callable,
)

from nexora.nodes.camera.camera_2d import Camera2D
from nexora.nodes.node import Node


if TYPE_CHECKING:
    from nexora.rendering.renderer import Renderer


Color = tuple[
    float,
    float,
    float,
]


# ==============================================================
# Easing
# ==============================================================


def _ease_linear(
    t: float,
) -> float:
    return t


def _ease_in(
    t: float,
) -> float:
    return t * t


def _ease_out(
    t: float,
) -> float:
    inverse = 1.0 - t

    return (
        1.0
        - inverse
        * inverse
    )


def _ease_in_out(
    t: float,
) -> float:
    if t < 0.5:
        return (
            2.0
            * t
            * t
        )

    return (
        1.0
        - (
            (
                -2.0
                * t
                + 2.0
            )
            ** 2
        )
        / 2.0
    )


_EASING_FUNCTIONS: dict[
    str,
    Callable[[float], float],
] = {
    "linear": _ease_linear,
    "ease_in": _ease_in,
    "ease_out": _ease_out,
    "ease_in_out": _ease_in_out,
}


# ==============================================================
# Camera step
# ==============================================================


@dataclass(slots=True)
class _CameraStep:
    """
    Internal cinematic sequence step.
    """

    kind: str

    duration: float = 0.0

    # ==========================================================
    # Transform
    # ==========================================================

    x: float | None = None
    y: float | None = None

    zoom: float | None = None

    target: Node | None = None

    # ==========================================================
    # Effects
    # ==========================================================

    color: Color | None = None

    alpha: float | None = None

    size: float | None = None

    # ==========================================================
    # Animation
    # ==========================================================

    easing: str = "ease_in_out"

    elapsed: float = 0.0

    started: bool = False

    # ==========================================================
    # Starting values
    # ==========================================================

    start_x: float = 0.0
    start_y: float = 0.0

    start_zoom: float = 1.0


# ==============================================================
# CinematicCamera2D
# ==============================================================


class CinematicCamera2D(Camera2D):
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
            _CameraStep
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
    # Movement queue
    # ==========================================================

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

    # ==========================================================
    # Zoom queue
    # ==========================================================

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

    # ==========================================================
    # Wait
    # ==========================================================

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

    # ==========================================================
    # Fade queue
    # ==========================================================

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

    # ==========================================================
    # Flash queue
    # ==========================================================

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

    # ==========================================================
    # Letterbox queue
    # ==========================================================

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

    # ==========================================================
    # Shake queue
    # ==========================================================

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

    # ==========================================================
    # Trauma queue
    # ==========================================================

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

    # ==========================================================
    # Punch queue
    # ==========================================================

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

    # ==========================================================
    # Validation
    # ==========================================================

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

    # ==========================================================
    # Step initialization
    # ==========================================================

    def _start_step(
        self,
        step: _CameraStep,
    ) -> None:
        step.started = True

        step.elapsed = 0.0

        # ------------------------------------------------------
        # Synchronize state with renderer camera.
        #
        # This is important in case something outside the
        # cinematic camera changed the renderer camera.
        # ------------------------------------------------------

        self._x = float(
            self.camera.x
        )

        self._y = float(
            self.camera.y
        )

        self._zoom = float(
            self.camera.zoom
        )

        step.start_x = self._x
        step.start_y = self._y

        step.start_zoom = self._zoom

        # ------------------------------------------------------
        # Fade out
        # ------------------------------------------------------

        if step.kind == "fade_out":
            color = (
                step.color
                if step.color is not None
                else (
                    0.0,
                    0.0,
                    0.0,
                )
            )

            Camera2D.fade_out(
                self,
                duration=step.duration,
                color=color,
                easing=step.easing,
            )

        # ------------------------------------------------------
        # Fade in
        # ------------------------------------------------------

        elif step.kind == "fade_in":
            Camera2D.fade_in(
                self,
                duration=step.duration,
                easing=step.easing,
            )

        # ------------------------------------------------------
        # Flash
        # ------------------------------------------------------

        elif step.kind == "flash":
            color = (
                step.color
                if step.color is not None
                else (
                    1.0,
                    1.0,
                    1.0,
                )
            )

            Camera2D.flash(
                self,
                color=color,
                alpha=(
                    1.0
                    if step.alpha is None
                    else step.alpha
                ),
                duration=step.duration,
            )

        # ------------------------------------------------------
        # Letterbox
        # ------------------------------------------------------

        elif step.kind == "letterbox":
            color = (
                step.color
                if step.color is not None
                else (
                    0.0,
                    0.0,
                    0.0,
                )
            )

            Camera2D.letterbox(
                self,
                (
                    80.0
                    if step.size is None
                    else step.size
                ),
                duration=step.duration,
                color=color,
                easing=step.easing,
            )

        # ------------------------------------------------------
        # Clear letterbox
        # ------------------------------------------------------

        elif step.kind == "clear_letterbox":
            Camera2D.clear_letterbox(
                self,
                duration=step.duration,
                easing=step.easing,
            )

        # ------------------------------------------------------
        # Shake
        # ------------------------------------------------------

        elif step.kind == "shake":
            Camera2D.shake(
                self,
                intensity=(
                    0.0
                    if step.alpha is None
                    else step.alpha
                ),
                duration=step.duration,
            )

        # ------------------------------------------------------
        # Trauma
        # ------------------------------------------------------

        elif step.kind == "trauma":
            Camera2D.add_trauma(
                self,
                (
                    0.0
                    if step.alpha is None
                    else step.alpha
                ),
            )

        # ------------------------------------------------------
        # Punch
        # ------------------------------------------------------

        elif step.kind == "punch":
            Camera2D.punch(
                self,
                (
                    0.0
                    if step.x is None
                    else step.x
                ),
                (
                    0.0
                    if step.y is None
                    else step.y
                ),
                duration=step.duration,
            )

    # ==========================================================
    # Interpolation
    # ==========================================================

    @staticmethod
    def _lerp_value(
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
    def _step_progress(
        step: _CameraStep,
    ) -> float:
        if step.duration <= 0.0:
            return 1.0

        return min(
            step.elapsed
            / step.duration,
            1.0,
        )

    # ==========================================================
    # Step update
    # ==========================================================

    def _update_step(
        self,
        step: _CameraStep,
        delta_time: float,
    ) -> bool:
        if not step.started:
            self._start_step(
                step
            )

        # ------------------------------------------------------
        # Immediate steps
        # ------------------------------------------------------

        if step.duration <= 0.0:
            return self._finish_immediate_step(
                step
            )

        # ------------------------------------------------------
        # Advance timer
        # ------------------------------------------------------

        step.elapsed += float(
            delta_time
        )

        progress = self._step_progress(
            step
        )

        easing_function = (
            _EASING_FUNCTIONS[
                step.easing
            ]
        )

        t = easing_function(
            progress
        )

        # ------------------------------------------------------
        # Wait
        # ------------------------------------------------------

        if step.kind == "wait":
            return (
                progress
                >= 1.0
            )

        # ------------------------------------------------------
        # Target position
        # ------------------------------------------------------

        target_x = step.x
        target_y = step.y

        if (
            step.kind == "move_target"
            and step.target is not None
        ):
            target_x, target_y = (
                step.target.world_position
            )

        # ------------------------------------------------------
        # Position interpolation
        # ------------------------------------------------------

        if step.kind in {
            "move",
            "move_target",
            "move_zoom",
            "transform",
        }:
            if (
                target_x is not None
                and target_y is not None
            ):
                x = self._lerp_value(
                    step.start_x,
                    float(
                        target_x
                    ),
                    t,
                )

                y = self._lerp_value(
                    step.start_y,
                    float(
                        target_y
                    ),
                    t,
                )

                self.set_position(
                    x,
                    y,
                )

        # ------------------------------------------------------
        # Zoom interpolation
        # ------------------------------------------------------

        if step.kind in {
            "zoom",
            "move_zoom",
            "transform",
        }:
            if step.zoom is not None:
                zoom = self._lerp_value(
                    step.start_zoom,
                    step.zoom,
                    t,
                )

                self.set_zoom(
                    zoom
                )

        # ------------------------------------------------------
        # Fade
        # ------------------------------------------------------

        if step.kind in {
            "fade_out",
            "fade_in",
        }:
            return (
                not self.is_fading
            )

        # ------------------------------------------------------
        # Flash
        # ------------------------------------------------------

        if step.kind == "flash":
            return (
                not self.is_flashing
            )

        # ------------------------------------------------------
        # Letterbox
        # ------------------------------------------------------

        if step.kind in {
            "letterbox",
            "clear_letterbox",
        }:
            return (
                not self._letterbox_active
            )

        # ------------------------------------------------------
        # Shake
        # ------------------------------------------------------

        if step.kind == "shake":
            return (
                progress
                >= 1.0
            )

        # ------------------------------------------------------
        # Trauma
        # ------------------------------------------------------

        if step.kind == "trauma":
            return (
                progress
                >= 1.0
            )

        # ------------------------------------------------------
        # Punch
        # ------------------------------------------------------

        if step.kind == "punch":
            return (
                not self._punch_active
            )

        # ------------------------------------------------------
        # Movement / zoom
        # ------------------------------------------------------

        return (
            progress
            >= 1.0
        )

    # ==========================================================
    # Immediate steps
    # ==========================================================

    def _finish_immediate_step(
        self,
        step: _CameraStep,
    ) -> bool:
        """
        Apply zero-duration sequence steps immediately.
        """

        # ------------------------------------------------------
        # Move
        # ------------------------------------------------------

        if step.kind == "move":
            if (
                step.x is not None
                and step.y is not None
            ):
                self.set_position(
                    step.x,
                    step.y,
                )

        # ------------------------------------------------------
        # Move to node
        # ------------------------------------------------------

        elif step.kind == "move_target":
            if step.target is not None:
                x, y = (
                    step.target.world_position
                )

                self.set_position(
                    x,
                    y,
                )

        # ------------------------------------------------------
        # Zoom
        # ------------------------------------------------------

        elif step.kind == "zoom":
            if step.zoom is not None:
                self.set_zoom(
                    step.zoom
                )

        # ------------------------------------------------------
        # Move + zoom
        # ------------------------------------------------------

        elif step.kind in {
            "move_zoom",
            "transform",
        }:
            if (
                step.x is not None
                and step.y is not None
            ):
                self.set_position(
                    step.x,
                    step.y,
                )

            if step.zoom is not None:
                self.set_zoom(
                    step.zoom
                )

        # ------------------------------------------------------
        # Wait
        # ------------------------------------------------------

        elif step.kind == "wait":
            pass

        # ------------------------------------------------------
        # Fade
        #
        # Camera2D already handles duration=0 immediately.
        # ------------------------------------------------------

        elif step.kind in {
            "fade_out",
            "fade_in",
        }:
            pass

        # ------------------------------------------------------
        # Letterbox
        #
        # Camera2D already handles duration=0 immediately.
        # ------------------------------------------------------

        elif step.kind in {
            "letterbox",
            "clear_letterbox",
        }:
            pass

        # ------------------------------------------------------
        # Trauma
        # ------------------------------------------------------

        elif step.kind == "trauma":
            pass

        return True

    # ==========================================================
    # Sequence update
    # ==========================================================

    def _update_sequence(
        self,
        delta_time: float,
    ) -> None:
        if not self.playing:
            return

        if not self._sequence:
            self.playing = False
            return

        if (
            self._current_step
            >= len(
                self._sequence
            )
        ):
            self._finish_sequence()
            return

        step = self._sequence[
            self._current_step
        ]

        finished = self._update_step(
            step,
            delta_time,
        )

        if not finished:
            return

        finished_index = (
            self._current_step
        )

        self._current_step += 1

        # ------------------------------------------------------
        # Step callback
        # ------------------------------------------------------

        if (
            self.on_step_finished
            is not None
        ):
            self.on_step_finished(
                finished_index
            )

        # ------------------------------------------------------
        # Sequence finished
        # ------------------------------------------------------

        if (
            self._current_step
            >= len(
                self._sequence
            )
        ):
            self._finish_sequence()

    # ==========================================================
    # Sequence finish
    # ==========================================================

    def _finish_sequence(
        self,
    ) -> None:
        if self.loop:
            self._current_step = 0

            self._reset_steps()

            self.playing = True

            return

        self.playing = False

        if (
            self.on_sequence_finished
            is not None
        ):
            self.on_sequence_finished()

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