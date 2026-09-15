from __future__ import annotations

import weakref

from nexora.signals import Signal


class Timer:
    """Runtime timer managed by :class:`TimerManager`.

    ``repeat`` is the number of additional timeouts after the first one.
    Use ``repeat=-1`` for an infinite repeating timer.
    """

    def __init__(
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
    ) -> None:
        duration = float(duration)
        if duration < 0.0:
            raise ValueError("Timer duration cannot be negative.")

        if interval is None:
            interval = duration
        interval = float(interval)
        if interval < 0.0:
            raise ValueError("Timer interval cannot be negative.")

        repeat = int(repeat)
        if repeat < -1:
            raise ValueError("Timer repeat must be -1 or greater.")

        if callback is not None and not callable(callback):
            raise TypeError("Timer callback must be callable.")

        self.duration = duration
        self.interval = interval
        self.repeat = repeat
        self.immediate = bool(immediate)
        self.ignore_time_scale = bool(ignore_time_scale)
        self.callback = callback

        self._elapsed = 0.0
        self._timeouts = 0
        self._active = bool(auto_start)
        self._paused = False
        self._started = False
        self._immediate_fired = False

        self._owner_ref = None
        self._owner_fallback = None
        if owner is not None:
            try:
                self._owner_ref = weakref.ref(owner)
            except TypeError:
                self._owner_fallback = owner

        self.started = Signal("timer.started", owner=owner)
        self.timeout = Signal("timer.timeout", owner=owner)
        self.finished = Signal("timer.finished", owner=owner)
        self.cancelled = Signal("timer.cancelled", owner=owner)

        tracker = getattr(owner, "_track_timer", None)
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
    def elapsed(self) -> float:
        return self._elapsed

    @property
    def timeout_count(self) -> int:
        return self._timeouts

    @property
    def remaining(self) -> float:
        target = self.duration if self._timeouts == 0 else self.interval
        return max(0.0, target - self._elapsed)

    def start(self, *, reset: bool = True) -> Timer:
        if reset:
            self._elapsed = 0.0
            self._timeouts = 0
            self._immediate_fired = False
        self._active = True
        self._paused = False
        self._started = False
        return self

    def restart(self) -> Timer:
        return self.start(reset=True)

    def pause(self) -> Timer:
        if self._active:
            self._paused = True
        return self

    def resume(self) -> Timer:
        if self._active:
            self._paused = False
        return self

    def cancel(self) -> Timer:
        if not self._active:
            return self
        self._active = False
        self._paused = False
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
        untracker = getattr(owner, "_untrack_timer", None)
        if untracker is not None:
            untracker(self)

    def _fire_timeout(self) -> None:
        self._timeouts += 1
        if self.callback is not None:
            self.callback()
        self.timeout.emit(self, self._timeouts)

    def _should_repeat(self) -> bool:
        if self.repeat == -1:
            return True
        # repeat is the number of additional fires after the first one.
        return self._timeouts <= self.repeat

    def _finish(self) -> None:
        if not self._active:
            return
        self._active = False
        self._paused = False
        self.finished.emit(self)
        self._untrack_owner()

    def update(self, scaled_delta: float, unscaled_delta: float) -> bool:
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

        if self.immediate and not self._immediate_fired:
            self._immediate_fired = True
            self._fire_timeout()
            if not self._should_repeat():
                self._finish()
                return False

        delta = float(
            unscaled_delta if self.ignore_time_scale else scaled_delta
        )
        if delta <= 0.0:
            return self._active

        self._elapsed += delta

        # Large frame deltas may cross more than one interval. Preserve the
        # remainder so repeating timers do not drift over time.
        while self._active:
            target = self.duration if self._timeouts == 0 else self.interval

            # A zero-duration/zero-interval infinite timer would otherwise
            # loop forever in a single update. Limit zero-length timers to a
            # single fire per engine tick.
            if target <= 0.0:
                self._fire_timeout()
                if not self._should_repeat():
                    self._finish()
                self._elapsed = 0.0
                break

            if self._elapsed < target:
                break

            self._elapsed -= target
            self._fire_timeout()

            if not self._should_repeat():
                self._finish()
                break

        return self._active
