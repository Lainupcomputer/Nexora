from __future__ import annotations

from .timer import Timer


class TimerManager:
    """Owns and updates runtime timers for the engine."""

    def __init__(self) -> None:
        self._timers: list[Timer] = []
        self._paused = False

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def active_count(self) -> int:
        return sum(1 for timer in self._timers if timer.active)

    @property
    def timers(self) -> tuple[Timer, ...]:
        return tuple(self._timers)

    def create(
        self,
        duration: float,
        callback=None,
        *,
        interval: float | None = None,
        repeat: int = 0,
        immediate: bool = False,
        ignore_time_scale: bool = False,
        owner: object | None = None,
        auto_start: bool = True,
    ) -> Timer:
        timer = Timer(
            duration,
            callback,
            interval=interval,
            repeat=repeat,
            immediate=immediate,
            ignore_time_scale=ignore_time_scale,
            owner=owner,
            auto_start=auto_start,
        )
        self._timers.append(timer)
        return timer

    def call_later(
        self,
        delay: float,
        callback,
        *,
        ignore_time_scale: bool = False,
        owner: object | None = None,
    ) -> Timer:
        return self.create(
            delay,
            callback,
            repeat=0,
            ignore_time_scale=ignore_time_scale,
            owner=owner,
        )

    def call_every(
        self,
        interval: float,
        callback,
        *,
        repeat: int = -1,
        immediate: bool = False,
        ignore_time_scale: bool = False,
        owner: object | None = None,
    ) -> Timer:
        return self.create(
            interval,
            callback,
            interval=interval,
            repeat=repeat,
            immediate=immediate,
            ignore_time_scale=ignore_time_scale,
            owner=owner,
        )

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def clear(self) -> None:
        for timer in tuple(self._timers):
            timer.cancel()
        self._timers.clear()

    def kill_owner(self, owner: object) -> int:
        killed = 0
        for timer in tuple(self._timers):
            if timer.owner is owner and timer.active:
                timer.cancel()
                killed += 1
        self._prune()
        return killed

    def update(self, scaled_delta: float, unscaled_delta: float) -> None:
        if self._paused:
            return

        for timer in tuple(self._timers):
            timer.update(scaled_delta, unscaled_delta)

        self._prune()

    def _prune(self) -> None:
        self._timers = [timer for timer in self._timers if timer.active]
