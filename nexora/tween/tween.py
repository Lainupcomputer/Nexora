from __future__ import annotations

import weakref
from collections.abc import Callable

from nexora.signals import Signal

from .accessor import PropertyAccessor
from .easing import EaseFunction, resolve_easing
from .interpolation import interpolate


class Tween:
    """Interpolates one property on one target."""

    def __init__(
        self,
        target: object,
        property_path: str,
        end_value,
        *,
        duration: float,
        easing: str | EaseFunction = "linear",
        delay: float = 0.0,
        loops: int = 0,
        yoyo: bool = False,
        owner: object | None = None,
        ignore_time_scale: bool = False,
        start_value=None,
        on_complete: Callable[[Tween], None] | None = None,
    ) -> None:
        duration = float(duration)
        delay = float(delay)
        loops = int(loops)

        if duration < 0.0:
            raise ValueError("Tween duration cannot be negative.")
        if delay < 0.0:
            raise ValueError("Tween delay cannot be negative.")
        if loops < -1:
            raise ValueError("Tween loops must be -1 or greater.")

        self.accessor = PropertyAccessor(target, property_path)
        self.target = target
        self.property_path = str(property_path)
        self.end_value = end_value
        self.duration = duration
        self.delay = delay
        self.loops = loops
        self.yoyo = bool(yoyo)
        self.ignore_time_scale = bool(ignore_time_scale)
        self.easing = resolve_easing(easing)

        self._explicit_start_value = start_value
        self._start_value = None
        self._elapsed = 0.0
        self._delay_elapsed = 0.0
        self._completed_loops = 0
        self._forward = True
        self._started = False
        self._paused = False
        self._active = True

        if owner is None:
            owner = target
        self._owner_ref = self._make_weakref(owner)
        self._owner_fallback = None if self._owner_ref is not None else owner

        self.started = Signal("tween.started", owner=owner)
        self.step = Signal("tween.step", owner=owner)
        self.looped = Signal("tween.looped", owner=owner)
        self.finished = Signal("tween.finished", owner=owner)
        self.stopped = Signal("tween.stopped", owner=owner)

        if on_complete is not None:
            self.finished.connect(on_complete)

        tracker = getattr(owner, "_track_tween", None)
        if tracker is not None:
            tracker(self)

    @staticmethod
    def _make_weakref(value):
        if value is None:
            return None
        try:
            return weakref.ref(value)
        except TypeError:
            return None

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
    def progress(self) -> float:
        if self.duration <= 0.0:
            return 1.0 if self._started else 0.0
        return max(0.0, min(1.0, self._elapsed / self.duration))

    def pause(self) -> Tween:
        self._paused = True
        return self

    def resume(self) -> Tween:
        self._paused = False
        return self

    def stop(self) -> Tween:
        if not self._active:
            return self
        self._active = False
        self.stopped.emit(self)
        self._untrack_owner()
        return self

    def complete(self) -> Tween:
        if not self._active:
            return self
        if not self._started:
            self._begin()
        value = self.end_value if self._forward else self._start_value
        self.accessor.set(value)
        self._active = False
        self.finished.emit(self)
        self._untrack_owner()
        return self

    def _untrack_owner(self) -> None:
        owner = self.owner
        untracker = getattr(owner, "_untrack_tween", None)
        if untracker is not None:
            untracker(self)

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

    def _begin(self) -> None:
        self._start_value = (
            self._explicit_start_value
            if self._explicit_start_value is not None
            else self.accessor.get()
        )
        self._started = True
        self.started.emit(self)

    def _apply(self) -> None:
        raw = 1.0 if self.duration <= 0.0 else self.progress
        eased = self.easing(raw)

        start = self._start_value if self._forward else self.end_value
        end = self.end_value if self._forward else self._start_value
        value = interpolate(start, end, eased)
        self.accessor.set(value)
        self.step.emit(self, raw, value)

    def update(self, scaled_delta: float, unscaled_delta: float) -> bool:
        if not self._active:
            return False
        if self._paused:
            return True
        if not self._owner_alive():
            self.stop()
            return False

        delta = float(unscaled_delta if self.ignore_time_scale else scaled_delta)
        if delta < 0.0:
            delta = 0.0

        if not self._started:
            if self._delay_elapsed < self.delay:
                self._delay_elapsed += delta
                if self._delay_elapsed < self.delay:
                    return True
                delta = max(0.0, self._delay_elapsed - self.delay)
            self._begin()

        if self.duration <= 0.0:
            self._elapsed = self.duration
            self._apply()
            return self._advance_cycle()

        self._elapsed += delta
        self._apply()

        while self._elapsed >= self.duration and self._active:
            overflow = self._elapsed - self.duration
            if not self._advance_cycle():
                return False
            self._elapsed = min(overflow, self.duration)
            self._apply()
            if overflow < self.duration:
                break

        return self._active

    def _advance_cycle(self) -> bool:
        has_more = self.loops == -1 or self._completed_loops < self.loops
        if has_more:
            self._completed_loops += 1
            if self.yoyo:
                self._forward = not self._forward
            self._elapsed = 0.0
            self.looped.emit(self, self._completed_loops)
            return True

        final_value = self.end_value if self._forward else self._start_value
        self.accessor.set(final_value)
        self._active = False
        self.finished.emit(self)
        self._untrack_owner()
        return False
