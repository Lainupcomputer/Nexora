from __future__ import annotations

import threading

from collections.abc import Callable
from typing import Any

from nexora.signals.signal import (
    Signal,
    SignalConnection,
)


class EventBus:
    """
    Named signal collection for decoupled application events.

    Node-specific communication should normally use explicit ``Signal``
    attributes. The bus is useful when sender and receiver should not
    know about each other at all.
    """

    def __init__(self) -> None:
        self._signals: dict[
            str,
            Signal,
        ] = {}
        self._lock = threading.RLock()

    def signal(
        self,
        name: str,
    ) -> Signal:
        key = self._normalize_name(
            name
        )

        with self._lock:
            signal = self._signals.get(
                key
            )

            if signal is None:
                signal = Signal(key)
                self._signals[key] = signal

            return signal

    def connect(
        self,
        name: str,
        callback: Callable[..., Any],
        *,
        owner: object | None = None,
        once: bool = False,
        priority: int = 0,
    ) -> SignalConnection:
        return self.signal(
            name
        ).connect(
            callback,
            owner=owner,
            once=once,
            priority=priority,
        )

    def emit(
        self,
        name: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.signal(name).emit(
            *args,
            **kwargs,
        )

    def clear(
        self,
        name: str | None = None,
    ) -> None:
        if name is not None:
            key = self._normalize_name(
                name
            )

            with self._lock:
                signal = self._signals.pop(
                    key,
                    None,
                )

            if signal is not None:
                signal.clear()

            return

        with self._lock:
            signals = tuple(
                self._signals.values()
            )
            self._signals.clear()

        for signal in signals:
            signal.clear()

    def has_signal(
        self,
        name: str,
    ) -> bool:
        key = self._normalize_name(
            name
        )

        with self._lock:
            return key in self._signals

    @staticmethod
    def _normalize_name(
        name: str,
    ) -> str:
        value = str(name).strip()

        if not value:
            raise ValueError(
                "Event name cannot be empty."
            )

        return value
