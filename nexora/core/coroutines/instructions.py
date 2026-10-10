from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class YieldInstruction:
    """Base object yielded by a Nexora coroutine task."""

    immediate = False

    def bind(self, task) -> None:
        self.task = task

    def update(
        self,
        scaled_delta: float,
        unscaled_delta: float,
    ) -> bool:
        raise NotImplementedError

    def result(self):
        return None

    def cancel(self) -> None:
        pass


class WaitSeconds(YieldInstruction):
    def __init__(
        self,
        duration: float,
        *,
        ignore_time_scale: bool | None = None,
    ) -> None:
        duration = float(duration)
        if duration < 0.0:
            raise ValueError(
                "Wait duration cannot be negative."
            )

        self.duration = duration
        self.ignore_time_scale = ignore_time_scale
        self.elapsed = 0.0
        self.task = None

    def update(
        self,
        scaled_delta: float,
        unscaled_delta: float,
    ) -> bool:
        ignore_time_scale = self.ignore_time_scale

        if ignore_time_scale is None:
            ignore_time_scale = bool(
                getattr(
                    self.task,
                    "ignore_time_scale",
                    False,
                )
            )

        delta = (
            unscaled_delta
            if ignore_time_scale
            else scaled_delta
        )

        self.elapsed += max(0.0, float(delta))
        return self.elapsed >= self.duration


class WaitFrames(YieldInstruction):
    def __init__(self, frames: int = 1) -> None:
        frames = int(frames)
        if frames < 1:
            raise ValueError(
                "WaitFrames requires at least one frame."
            )

        self.frames = frames
        self.remaining = frames
        self.task = None

    def update(
        self,
        scaled_delta: float,
        unscaled_delta: float,
    ) -> bool:
        del scaled_delta, unscaled_delta
        self.remaining -= 1
        return self.remaining <= 0


class WaitUntil(YieldInstruction):
    def __init__(
        self,
        predicate: Callable[[], Any],
    ) -> None:
        if not callable(predicate):
            raise TypeError(
                "WaitUntil predicate must be callable."
            )

        self.predicate = predicate
        self.value = None
        self.task = None

    def update(
        self,
        scaled_delta: float,
        unscaled_delta: float,
    ) -> bool:
        del scaled_delta, unscaled_delta
        self.value = self.predicate()
        return bool(self.value)

    def result(self):
        return self.value


@dataclass(frozen=True, slots=True)
class SignalResult:
    args: tuple[Any, ...]
    kwargs: dict[str, Any]

    @property
    def value(self):
        if self.kwargs:
            return self

        if len(self.args) == 0:
            return None

        if len(self.args) == 1:
            return self.args[0]

        return self.args


class WaitSignal(YieldInstruction):
    def __init__(self, signal) -> None:
        connect = getattr(signal, "connect", None)
        if not callable(connect):
            raise TypeError(
                "wait_signal() expects a Signal-like object."
            )

        self.signal = signal
        self.connection = None
        self._ready = False
        self._result = SignalResult((), {})
        self.task = None

    def bind(self, task) -> None:
        super().bind(task)

        self.connection = self.signal.connect(
            self._on_signal,
            once=True,
        )

    def _on_signal(self, *args, **kwargs) -> None:
        self._result = SignalResult(
            tuple(args),
            dict(kwargs),
        )
        self._ready = True

    def update(
        self,
        scaled_delta: float,
        unscaled_delta: float,
    ) -> bool:
        del scaled_delta, unscaled_delta
        return self._ready

    def result(self):
        return self._result.value

    def cancel(self) -> None:
        connection = self.connection
        self.connection = None

        if connection is not None:
            disconnect = getattr(
                connection,
                "disconnect",
                None,
            )
            if callable(disconnect):
                disconnect()


class WaitRuntimeObject(YieldInstruction):
    """Wait until a Tween, Timer, Task or similar object's active flag clears."""

    def __init__(self, obj) -> None:
        self.obj = obj
        self.task = None

    def update(
        self,
        scaled_delta: float,
        unscaled_delta: float,
    ) -> bool:
        del scaled_delta, unscaled_delta
        return not bool(
            getattr(
                self.obj,
                "active",
                False,
            )
        )

    def result(self):
        return self.obj


class ImmediateCall(YieldInstruction):
    immediate = True

    def __init__(
        self,
        callback: Callable[..., Any],
        *args,
        **kwargs,
    ) -> None:
        if not callable(callback):
            raise TypeError(
                "call() callback must be callable."
            )

        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.value = None
        self.task = None

    def update(
        self,
        scaled_delta: float,
        unscaled_delta: float,
    ) -> bool:
        del scaled_delta, unscaled_delta
        self.value = self.callback(
            *self.args,
            **self.kwargs,
        )
        return True

    def result(self):
        return self.value


def wait(
    duration: float,
    *,
    ignore_time_scale: bool | None = None,
) -> WaitSeconds:
    return WaitSeconds(
        duration,
        ignore_time_scale=ignore_time_scale,
    )


def wait_seconds(
    duration: float,
    *,
    ignore_time_scale: bool | None = None,
) -> WaitSeconds:
    return wait(
        duration,
        ignore_time_scale=ignore_time_scale,
    )


def wait_frames(frames: int = 1) -> WaitFrames:
    return WaitFrames(frames)


def next_frame() -> WaitFrames:
    return WaitFrames(1)


def wait_until(
    predicate: Callable[[], Any],
) -> WaitUntil:
    return WaitUntil(predicate)


def wait_signal(signal) -> WaitSignal:
    return WaitSignal(signal)


def wait_tween(tween) -> WaitRuntimeObject:
    return WaitRuntimeObject(tween)


def wait_timer(timer) -> WaitRuntimeObject:
    return WaitRuntimeObject(timer)


def wait_task(task) -> WaitRuntimeObject:
    return WaitRuntimeObject(task)


def call(
    callback: Callable[..., Any],
    *args,
    **kwargs,
) -> ImmediateCall:
    return ImmediateCall(
        callback,
        *args,
        **kwargs,
    )
