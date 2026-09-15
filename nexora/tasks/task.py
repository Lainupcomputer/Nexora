from __future__ import annotations

import inspect
import weakref

from nexora.signals import Signal

from .instructions import (
    YieldInstruction,
    WaitFrames,
)


class CoroutineTask:
    """Cooperative generator task updated by :class:`TaskManager`."""

    def __init__(
        self,
        routine,
        *,
        owner: object | None = None,
        ignore_time_scale: bool = False,
        name: str | None = None,
    ) -> None:
        if not inspect.isgenerator(routine):
            raise TypeError(
                "CoroutineTask requires a generator object."
            )

        self._routine = routine
        self.ignore_time_scale = bool(
            ignore_time_scale
        )
        self.name = (
            str(name)
            if name is not None
            else getattr(
                getattr(routine, "gi_code", None),
                "co_name",
                "task",
            )
        )

        self._active = True
        self._paused = False
        self._started = False
        self._instruction: YieldInstruction | None = None
        self._pending_send = None
        self._has_pending_send = False
        self._result = None
        self._exception: BaseException | None = None

        self._owner_ref = None
        self._owner_fallback = None

        if owner is not None:
            try:
                self._owner_ref = weakref.ref(owner)
            except TypeError:
                self._owner_fallback = owner

        self.started = Signal(
            "task.started",
            owner=owner,
        )
        self.yielded = Signal(
            "task.yielded",
            owner=owner,
        )
        self.finished = Signal(
            "task.finished",
            owner=owner,
        )
        self.cancelled = Signal(
            "task.cancelled",
            owner=owner,
        )
        self.failed = Signal(
            "task.failed",
            owner=owner,
        )

        tracker = getattr(
            owner,
            "_track_task",
            None,
        )
        if tracker is not None:
            tracker(self)

    @property
    def owner(self):
        if self._owner_ref is not None:
            return self._owner_ref()
        return self._owner_fallback

    @property
    def active(self) -> bool:
        return self._active

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def done(self) -> bool:
        return not self._active

    @property
    def result(self):
        return self._result

    @property
    def exception(self) -> BaseException | None:
        return self._exception

    @property
    def current_instruction(
        self,
    ) -> YieldInstruction | None:
        return self._instruction

    def pause(self) -> CoroutineTask:
        if self._active:
            self._paused = True
        return self

    def resume(self) -> CoroutineTask:
        if self._active:
            self._paused = False
        return self

    def cancel(self) -> CoroutineTask:
        if not self._active:
            return self

        self._cleanup_instruction()
        self._active = False
        self._paused = False

        try:
            self._routine.close()
        finally:
            self.cancelled.emit(self)
            self._untrack_owner()

        return self

    stop = cancel

    def _owner_alive(self) -> bool:
        owner = self.owner

        if owner is None and self._owner_ref is not None:
            return False

        if owner is None:
            return True

        world = getattr(owner, "world", None)
        entity = getattr(owner, "entity", None)
        is_alive = getattr(world, "is_alive", None)

        if entity is not None and callable(is_alive):
            try:
                return bool(is_alive(entity))
            except Exception:
                return True

        return True

    def _untrack_owner(self) -> None:
        owner = self.owner
        untracker = getattr(
            owner,
            "_untrack_task",
            None,
        )
        if untracker is not None:
            untracker(self)

    def _cleanup_instruction(self) -> None:
        instruction = self._instruction
        self._instruction = None

        if instruction is not None:
            instruction.cancel()

    def _finish(self, result=None) -> None:
        if not self._active:
            return

        self._cleanup_instruction()
        self._active = False
        self._paused = False
        self._result = result
        self.finished.emit(self, result)
        self._untrack_owner()

    def _fail(self, error: BaseException) -> None:
        self._cleanup_instruction()
        self._active = False
        self._paused = False
        self._exception = error
        self.failed.emit(self, error)
        self._untrack_owner()

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
            self.cancel()
            return False

        if not self._started:
            self._started = True
            self.started.emit(self)

        instruction = self._instruction

        if instruction is not None:
            if not instruction.update(
                float(scaled_delta),
                float(unscaled_delta),
            ):
                return True

            self._pending_send = instruction.result()
            self._has_pending_send = True
            self._cleanup_instruction()

        try:
            self._run_until_blocked()
        except StopIteration as stop:
            self._finish(stop.value)
        except BaseException as error:
            self._fail(error)
            raise

        return self._active

    def _run_until_blocked(self) -> None:
        while self._active:
            if self._has_pending_send:
                yielded = self._routine.send(
                    self._pending_send
                )
                self._pending_send = None
                self._has_pending_send = False
            else:
                yielded = next(self._routine)

            if yielded is None:
                yielded = WaitFrames(1)

            if not isinstance(
                yielded,
                YieldInstruction,
            ):
                raise TypeError(
                    "Coroutine tasks must yield a Nexora "
                    "YieldInstruction or None."
                )

            yielded.bind(self)
            self.yielded.emit(self, yielded)

            if yielded.immediate:
                yielded.update(0.0, 0.0)
                self._pending_send = yielded.result()
                self._has_pending_send = True
                yielded.cancel()
                continue

            self._instruction = yielded
            return
