from __future__ import annotations

from nexora.nodes.camera.camera_2d import Camera2D
from nexora.nodes.camera.easing import EASING_FUNCTIONS as _EASING_FUNCTIONS
from nexora.nodes.camera.interpolation import lerp_value
from nexora.nodes.camera.cinematic_step import _CameraStep


class CinematicSequenceMixin:
    """Internal execution engine for CinematicCamera2D sequences."""

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

    @staticmethod
    def _lerp_value(
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

