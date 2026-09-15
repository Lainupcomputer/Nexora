from __future__ import annotations

from collections.abc import Callable

from nexora.animation.clip import (
    AnimationClip,
    AnimationFrame,
    AnimationEvent,
)


class Animator:
    """
    Runtime animation controller.

    The Animator owns playback state but does not render anything.
    """

    _TIME_EPSILON = 1e-9

    def __init__(
        self,
    ) -> None:
        self._clips: dict[
            str,
            AnimationClip,
        ] = {}

        self._clip: AnimationClip | None = None

        self._frame_index: int = 0
        self._frame_time: float = 0.0

        self._playing: bool = False
        self._finished: bool = False

        self.speed: float = 1.0

        self.on_frame_changed: (
            Callable[
                [AnimationFrame],
                None,
            ]
            | None
        ) = None

        self.on_event: (
            Callable[[AnimationEvent], None] | None
        ) = None

        self.on_finished: (
            Callable[
                [AnimationClip],
                None,
            ]
            | None
        ) = None

    # ==========================================================
    # Clips
    # ==========================================================

    def add_clip(
        self,
        clip: AnimationClip,
    ) -> None:
        self._clips[
            clip.name
        ] = clip

    def remove_clip(
        self,
        name: str,
    ) -> None:
        if (
            self._clip is not None
            and self._clip.name == name
        ):
            self.stop()

        self._clips.pop(
            name,
            None,
        )

    def get_clip(
        self,
        name: str,
    ) -> AnimationClip | None:
        return self._clips.get(
            name
        )

    def has_clip(
        self,
        name: str,
    ) -> bool:
        return name in self._clips

    # ==========================================================
    # Playback
    # ==========================================================

    def play(
        self,
        name: str,
        *,
        restart: bool = False,
    ) -> None:
        clip = self._clips.get(
            name
        )

        if clip is None:
            raise KeyError(
                f"Animation clip not found: {name}"
            )

        if (
            self._clip is clip
            and not restart
        ):
            self._playing = True
            return

        self._clip = clip

        self._frame_index = 0
        self._frame_time = 0.0

        self._playing = True
        self._finished = False

        self._emit_frame_changed()

    def pause(
        self,
    ) -> None:
        self._playing = False

    def resume(
        self,
    ) -> None:
        if (
            self._clip is not None
            and not self._finished
        ):
            self._playing = True

    def stop(
        self,
    ) -> None:
        self._playing = False

        self._clip = None

        self._frame_index = 0
        self._frame_time = 0.0

        self._finished = False

    def reset(
        self,
    ) -> None:
        self._frame_index = 0
        self._frame_time = 0.0

        self._finished = False

        if self._clip is not None:
            self._emit_frame_changed()

    # ==========================================================
    # Update
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        if not self._playing:
            return

        if self._clip is None:
            return

        if self._finished:
            return

        delta_time = float(
            delta_time
        )

        if delta_time <= 0.0:
            return

        speed = max(
            0.0,
            float(
                self.speed
            ),
        )

        if speed <= 0.0:
            return

        self._frame_time += (
            delta_time
            * speed
        )

        # ------------------------------------------------------
        # Consume complete frames.
        #
        # Floating point calculations such as:
        #
        #     0.1 + 0.1 + 0.1
        #
        # are not guaranteed to equal exactly 0.3.
        #
        # Therefore an epsilon is used when testing whether the
        # current frame duration has been reached.
        # ------------------------------------------------------

        while True:
            current = (
                self.current_frame
            )

            if current is None:
                return

            if (
                self._frame_time
                + self._TIME_EPSILON
                < current.duration
            ):
                break

            self._frame_time -= (
                current.duration
            )

            # Remove tiny floating point leftovers around zero.
            if (
                abs(
                    self._frame_time
                )
                <= self._TIME_EPSILON
            ):
                self._frame_time = 0.0

            if not self._advance_frame():
                break

    # ==========================================================
    # Frame advancement
    # ==========================================================

    def _advance_frame(
        self,
    ) -> bool:
        if self._clip is None:
            return False

        next_index = (
            self._frame_index
            + 1
        )

        # ------------------------------------------------------
        # Normal next frame
        # ------------------------------------------------------

        if (
            next_index
            < self._clip.frame_count
        ):
            self._frame_index = (
                next_index
            )

            self._emit_frame_changed()

            return True

        # ------------------------------------------------------
        # Loop
        # ------------------------------------------------------

        if self._clip.loop:
            self._frame_index = 0

            self._emit_frame_changed()

            return True

        # ------------------------------------------------------
        # Finished
        # ------------------------------------------------------

        self._frame_index = (
            self._clip.frame_count
            - 1
        )

        self._frame_time = 0.0

        self._playing = False
        self._finished = True

        if self.on_finished is not None:
            self.on_finished(
                self._clip
            )

        return False

    # ==========================================================
    # Events
    # ==========================================================

    def _emit_frame_changed(
        self,
    ) -> None:
        frame = (
            self.current_frame
        )

        if frame is None:
            return

        if self.on_frame_changed is not None:
            self.on_frame_changed(frame)

        if self._clip is not None and self.on_event is not None:
            for event in self._clip.events_for_frame(self._frame_index):
                self.on_event(event)

    # ==========================================================
    # State
    # ==========================================================

    @property
    def current_clip(
        self,
    ) -> AnimationClip | None:
        return self._clip

    @property
    def current_frame(
        self,
    ) -> AnimationFrame | None:
        if self._clip is None:
            return None

        return self._clip.frames[
            self._frame_index
        ]

    @property
    def frame_index(
        self,
    ) -> int:
        return self._frame_index

    @property
    def playing(
        self,
    ) -> bool:
        return self._playing

    @property
    def finished(
        self,
    ) -> bool:
        return self._finished

    @property
    def current_animation(self) -> AnimationClip | None:
        return self._clip

    @property
    def speed_scale(self) -> float:
        return self.speed

    @speed_scale.setter
    def speed_scale(self, value: float) -> None:
        self.speed = float(value)

    # ==========================================================
    # Progress
    # ==========================================================

    @property
    def progress(
        self,
    ) -> float:
        if self._clip is None:
            return 0.0

        total = (
            self._clip.duration
        )

        if total <= 0.0:
            return 0.0

        if self._finished:
            return 1.0

        elapsed = sum(
            frame.duration
            for frame
            in self._clip.frames[
                :self._frame_index
            ]
        )

        elapsed += (
            self._frame_time
        )

        return min(
            1.0,
            max(
                0.0,
                elapsed / total,
            ),
        )