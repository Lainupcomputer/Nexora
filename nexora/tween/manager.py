from __future__ import annotations

import threading

from .sequence import TweenSequence
from .tween import Tween


class TweenManager:
    """Global runtime owner for active tweens and sequences."""

    def __init__(self) -> None:
        self._items: list[object] = []
        self._pending: list[object] = []
        self._updating = False
        self._paused = False
        self._lock = threading.RLock()

    @property
    def active_count(self) -> int:
        with self._lock:
            return sum(1 for item in self._items if getattr(item, "active", False)) + sum(
                1 for item in self._pending if getattr(item, "active", False)
            )

    def to(
        self,
        target,
        property_path: str,
        end_value,
        *,
        duration: float,
        easing="linear",
        delay: float = 0.0,
        loops: int = 0,
        yoyo: bool = False,
        owner=None,
        ignore_time_scale: bool = False,
        on_complete=None,
    ) -> Tween:
        tween = Tween(
            target,
            property_path,
            end_value,
            duration=duration,
            easing=easing,
            delay=delay,
            loops=loops,
            yoyo=yoyo,
            owner=owner,
            ignore_time_scale=ignore_time_scale,
            on_complete=on_complete,
        )
        self.add(tween)
        return tween

    def from_to(
        self,
        target,
        property_path: str,
        start_value,
        end_value,
        *,
        duration: float,
        easing="linear",
        delay: float = 0.0,
        loops: int = 0,
        yoyo: bool = False,
        owner=None,
        ignore_time_scale: bool = False,
        on_complete=None,
    ) -> Tween:
        accessor_target = target
        # Set immediately so the visible state is deterministic before the
        # first manager update.
        from .accessor import PropertyAccessor
        PropertyAccessor(accessor_target, property_path).set(start_value)

        tween = Tween(
            target,
            property_path,
            end_value,
            duration=duration,
            easing=easing,
            delay=delay,
            loops=loops,
            yoyo=yoyo,
            owner=owner,
            ignore_time_scale=ignore_time_scale,
            start_value=start_value,
            on_complete=on_complete,
        )
        self.add(tween)
        return tween

    def sequence(
        self,
        *,
        owner=None,
        ignore_time_scale: bool = False,
        loops: int = 0,
        yoyo: bool = False,
    ) -> TweenSequence:
        sequence = TweenSequence(
            owner=owner,
            ignore_time_scale=ignore_time_scale,
            loops=loops,
            yoyo=yoyo,
        )
        self.add(sequence)
        return sequence

    def add(self, item):
        with self._lock:
            if self._updating:
                self._pending.append(item)
            else:
                self._items.append(item)
        return item

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def clear(self) -> None:
        with self._lock:
            items = tuple(self._items) + tuple(self._pending)
            self._items.clear()
            self._pending.clear()
        for item in items:
            stop = getattr(item, "stop", None)
            if stop is not None:
                stop()

    def kill_owner(self, owner) -> int:
        count = 0
        with self._lock:
            items = tuple(self._items) + tuple(self._pending)
        for item in items:
            if getattr(item, "owner", None) is owner and getattr(item, "active", False):
                item.stop()
                count += 1
        return count

    def update(self, scaled_delta: float, unscaled_delta: float | None = None) -> None:
        if self._paused:
            return
        if unscaled_delta is None:
            unscaled_delta = scaled_delta

        with self._lock:
            self._updating = True
            items = tuple(self._items)

        survivors: list[object] = []
        try:
            for item in items:
                update = getattr(item, "update", None)
                if update is None:
                    continue
                if update(float(scaled_delta), float(unscaled_delta)):
                    survivors.append(item)
        finally:
            with self._lock:
                self._items = survivors
                if self._pending:
                    self._items.extend(self._pending)
                    self._pending.clear()
                self._updating = False
