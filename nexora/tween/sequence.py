from __future__ import annotations

from dataclasses import dataclass
import weakref

from nexora.signals import Signal

from .tween import Tween


@dataclass(slots=True)
class _WaitStep:
    duration: float


@dataclass(slots=True)
class _TweenStep:
    target: object
    property_path: str
    end_value: object
    kwargs: dict
    start_value: object = None
    has_start_value: bool = False


@dataclass(slots=True)
class _CallbackStep:
    callback: object


class TweenSequence:
    def __init__(
        self,
        *,
        owner: object | None = None,
        ignore_time_scale: bool = False,
        loops: int = 0,
        yoyo: bool = False,
    ) -> None:
        if int(loops) < -1:
            raise ValueError(
                "Sequence loops must be -1 or greater."
            )

        self.ignore_time_scale = bool(
            ignore_time_scale
        )

        self.loops = int(
            loops
        )

        self.yoyo = bool(
            yoyo
        )

        self._steps: list[
            object
        ] = []

        self._index = 0
        self._wait_elapsed = 0.0

        self._current_tween: (
            Tween | None
        ) = None

        self._paused = False
        self._active = True
        self._started = False

        self._completed_loops = 0
        self._forward = True

        self._owner_ref = None
        self._owner_fallback = None

        if owner is not None:
            try:
                self._owner_ref = (
                    weakref.ref(
                        owner
                    )
                )

            except TypeError:
                self._owner_fallback = (
                    owner
                )

        self.started = Signal(
            "tween_sequence.started",
            owner=owner,
        )

        self.step_started = Signal(
            "tween_sequence.step_started",
            owner=owner,
        )

        self.looped = Signal(
            "tween_sequence.looped",
            owner=owner,
        )

        self.finished = Signal(
            "tween_sequence.finished",
            owner=owner,
        )

        self.stopped = Signal(
            "tween_sequence.stopped",
            owner=owner,
        )

        tracker = getattr(
            owner,
            "_track_tween",
            None,
        )

        if tracker is not None:
            tracker(
                self
            )

    # ==========================================================
    # PROPERTIES
    # ==========================================================

    @property
    def owner(
        self,
    ):
        if self._owner_ref is not None:
            return self._owner_ref()

        return self._owner_fallback

    @property
    def active(
        self,
    ) -> bool:
        return self._active

    @property
    def paused(
        self,
    ) -> bool:
        return self._paused

    # ==========================================================
    # BUILD SEQUENCE
    # ==========================================================

    def to(
        self,
        target,
        property_path: str,
        end_value,
        *,
        duration: float,
        **kwargs,
    ) -> TweenSequence:
        kwargs = dict(
            kwargs
        )

        kwargs.setdefault(
            "ignore_time_scale",
            self.ignore_time_scale,
        )

        kwargs.pop(
            "owner",
            None,
        )

        self._steps.append(
            _TweenStep(
                target,
                property_path,
                end_value,
                {
                    "duration": duration,
                    **kwargs,
                },
            )
        )

        return self

    def wait(
        self,
        duration: float,
    ) -> TweenSequence:
        duration = float(
            duration
        )

        if duration < 0.0:
            raise ValueError(
                "Sequence wait duration cannot be negative."
            )

        self._steps.append(
            _WaitStep(
                duration
            )
        )

        return self

    def call(
        self,
        callback,
    ) -> TweenSequence:
        if not callable(
            callback
        ):
            raise TypeError(
                "Sequence callback must be callable."
            )

        self._steps.append(
            _CallbackStep(
                callback
            )
        )

        return self

    # ==========================================================
    # CONTROL
    # ==========================================================

    def pause(
        self,
    ) -> TweenSequence:
        self._paused = True

        if self._current_tween is not None:
            self._current_tween.pause()

        return self

    def resume(
        self,
    ) -> TweenSequence:
        self._paused = False

        if self._current_tween is not None:
            self._current_tween.resume()

        return self

    def stop(
        self,
    ) -> TweenSequence:
        if not self._active:
            return self

        if self._current_tween is not None:
            self._current_tween.stop()
            self._current_tween = None

        self._active = False

        self.stopped.emit(
            self
        )

        self._untrack_owner()

        return self

    # ==========================================================
    # OWNER
    # ==========================================================

    def _untrack_owner(
        self,
    ) -> None:
        owner = self.owner

        untracker = getattr(
            owner,
            "_untrack_tween",
            None,
        )

        if untracker is not None:
            untracker(
                self
            )

    def _owner_alive(
        self,
    ) -> bool:
        owner = self.owner

        if (
            owner is None
            and self._owner_ref is not None
        ):
            return False

        if owner is None:
            return True

        world = getattr(
            owner,
            "world",
            None,
        )

        entity = getattr(
            owner,
            "entity",
            None,
        )

        is_alive = getattr(
            world,
            "is_alive",
            None,
        )

        if (
            entity is not None
            and callable(
                is_alive
            )
        ):
            try:
                return bool(
                    is_alive(
                        entity
                    )
                )

            except Exception:
                return True

        return True

    # ==========================================================
    # STEP ORDER
    # ==========================================================

    def _ordered_steps(
        self,
    ) -> list[object]:
        if self._forward:
            return self._steps

        return list(
            reversed(
                self._steps
            )
        )

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        scaled_delta: float,
        unscaled_delta: float,
    ) -> bool:
        if not self._active:
            return False

        if self._paused:
            return True

        if not self._owner_alive():
            self.stop()
            return False

        if not self._steps:
            self._finish()
            return False

        if not self._started:
            self._started = True

            self.started.emit(
                self
            )

        delta = float(
            unscaled_delta
            if self.ignore_time_scale
            else scaled_delta
        )

        steps = (
            self._ordered_steps()
        )

        while self._active:
            # --------------------------------------------------
            # END OF CURRENT CYCLE
            # --------------------------------------------------

            if (
                self._index
                >= len(steps)
            ):
                if not self._advance_cycle():
                    return False

                steps = (
                    self._ordered_steps()
                )

                continue

            step = (
                steps[
                    self._index
                ]
            )

            # --------------------------------------------------
            # WAIT
            # --------------------------------------------------

            if isinstance(
                step,
                _WaitStep,
            ):
                self._wait_elapsed += max(
                    0.0,
                    delta,
                )

                if (
                    self._wait_elapsed
                    < step.duration
                ):
                    return True

                self._wait_elapsed = 0.0
                self._index += 1

                self.step_started.emit(
                    self,
                    self._index,
                )

                # The wait consumed the frame's delta.
                # Callbacks may still run this tick,
                # but a following tween must not receive
                # the same delta again.
                delta = 0.0
                scaled_delta = 0.0
                unscaled_delta = 0.0

                continue

            # --------------------------------------------------
            # CALLBACK
            # --------------------------------------------------

            if isinstance(
                step,
                _CallbackStep,
            ):
                step.callback()

                self._index += 1

                self.step_started.emit(
                    self,
                    self._index,
                )

                continue

            # --------------------------------------------------
            # TWEEN
            # --------------------------------------------------

            if isinstance(
                step,
                _TweenStep,
            ):
                if (
                    self._current_tween
                    is None
                ):
                    kwargs = dict(
                        step.kwargs
                    )

                    from .accessor import (
                        PropertyAccessor,
                    )

                    accessor = (
                        PropertyAccessor(
                            step.target,
                            step.property_path,
                        )
                    )

                    if self._forward:
                        if (
                            not step.has_start_value
                        ):
                            step.start_value = (
                                accessor.get()
                            )

                            step.has_start_value = (
                                True
                            )

                        end_value = (
                            step.end_value
                        )

                    else:
                        end_value = (
                            step.start_value
                        )

                    self._current_tween = Tween(
                        step.target,
                        step.property_path,
                        end_value,
                        owner=None,
                        **kwargs,
                    )

                    self.step_started.emit(
                        self,
                        self._index,
                    )

                child = (
                    self._current_tween
                )

                child.update(
                    scaled_delta,
                    unscaled_delta,
                )

                if child.active:
                    return True

                self._current_tween = None
                self._index += 1

                # The child tween has finished this frame.
                #
                # We still continue the sequence loop so that:
                #
                # - callbacks after the tween may run immediately
                # - the sequence can finish immediately if this was
                #   the last step
                # - loops can advance without requiring another frame
                #
                # The consumed frame delta must not be applied to the
                # following step again.
                delta = 0.0
                scaled_delta = 0.0
                unscaled_delta = 0.0

                continue

        return self._active

    # ==========================================================
    # CYCLE
    # ==========================================================

    def _advance_cycle(
        self,
    ) -> bool:
        has_more = (
            self.loops == -1
            or self._completed_loops
            < self.loops
        )

        if not has_more:
            self._finish()
            return False

        self._completed_loops += 1

        if self.yoyo:
            self._forward = (
                not self._forward
            )

        self._index = 0
        self._wait_elapsed = 0.0
        self._current_tween = None

        self.looped.emit(
            self,
            self._completed_loops,
        )

        return True

    # ==========================================================
    # FINISH
    # ==========================================================

    def _finish(
        self,
    ) -> None:
        if not self._active:
            return

        self._active = False
        self._current_tween = None

        self.finished.emit(
            self
        )

        self._untrack_owner()