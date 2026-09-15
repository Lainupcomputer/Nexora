from __future__ import annotations

import inspect
import itertools
import threading
import weakref

from collections.abc import Callable
from typing import Any, Generic, TypeVar


T = TypeVar("T")


class SignalConnection:
    """
    Handle returned by :meth:`Signal.connect`.

    A connection can be disconnected or temporarily blocked without
    knowing the callback again. Bound-method callbacks are weakly held,
    so a signal does not keep their owner alive by itself.
    """

    __slots__ = (
        "_signal_ref",
        "_callback_ref",
        "_callback_strong",
        "_owner_ref",
        "once",
        "priority",
        "order",
        "blocked",
        "_connected",
        "__weakref__",
    )

    def __init__(
        self,
        signal: Signal,
        callback: Callable[..., Any],
        *,
        owner: object | None,
        once: bool,
        priority: int,
        order: int,
    ) -> None:
        self._signal_ref = weakref.ref(signal)

        self._callback_ref: (
            weakref.WeakMethod | None
        ) = None
        self._callback_strong: (
            Callable[..., Any] | None
        ) = None

        if (
            inspect.ismethod(callback)
            and callback.__self__ is not None
        ):
            self._callback_ref = (
                weakref.WeakMethod(callback)
            )
        else:
            self._callback_strong = callback

        self._owner_ref: (
            weakref.ReferenceType | None
        ) = None

        if owner is not None:
            try:
                self._owner_ref = weakref.ref(owner)
            except TypeError:
                # Some user objects intentionally do not support
                # weak references. The connection still works; it
                # simply cannot auto-untrack itself from that owner.
                self._owner_ref = None

        self.once = bool(once)
        self.priority = int(priority)
        self.order = int(order)
        self.blocked = False
        self._connected = True

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def callback(
        self,
    ) -> Callable[..., Any] | None:
        if self._callback_ref is not None:
            return self._callback_ref()

        return self._callback_strong

    @property
    def owner(self) -> object | None:
        if self._owner_ref is None:
            return None

        return self._owner_ref()

    def disconnect(self) -> None:
        signal = self._signal_ref()

        if signal is None:
            self._connected = False
            return

        signal._disconnect_connection(self)

    def block(self) -> None:
        self.blocked = True

    def unblock(self) -> None:
        self.blocked = False

    def __enter__(self) -> SignalConnection:
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.disconnect()


class Signal(Generic[T]):
    """
    Thread-safe synchronous signal.

    ``emit()`` calls listeners in priority order. Higher priorities run
    first; listeners with equal priority keep connection order.

    Examples::

        changed = Signal("changed")
        changed.connect(on_changed)
        changed.emit(10)

        # One-shot listener
        changed.connect(on_first_change, once=True)

    When a bound method belongs to a Nexora Node, its Node is inferred as
    the connection owner. Destroying that Node therefore disconnects the
    listener automatically.
    """

    __slots__ = (
        "name",
        "_connections",
        "_lock",
        "_order",
        "_owner_ref",
        "__weakref__",
    )

    def __init__(
        self,
        name: str | None = None,
        *,
        owner: object | None = None,
    ) -> None:
        self.name = (
            str(name)
            if name is not None
            else "signal"
        )

        self._connections: list[
            SignalConnection
        ] = []

        self._lock = threading.RLock()
        self._order = itertools.count()

        self._owner_ref: (
            weakref.ReferenceType | None
        ) = None

        if owner is not None:
            try:
                self._owner_ref = weakref.ref(owner)
            except TypeError:
                self._owner_ref = None

            tracker = getattr(
                owner,
                "_track_owned_signal",
                None,
            )

            if tracker is not None:
                tracker(self)

    @property
    def owner(self) -> object | None:
        if self._owner_ref is None:
            return None

        return self._owner_ref()

    def connect(
        self,
        callback: Callable[..., Any],
        *,
        owner: object | None = None,
        once: bool = False,
        priority: int = 0,
    ) -> SignalConnection:
        if not callable(callback):
            raise TypeError(
                "Signal callback must be callable."
            )

        if owner is None:
            owner = getattr(
                callback,
                "__self__",
                None,
            )

        connection = SignalConnection(
            self,
            callback,
            owner=owner,
            once=once,
            priority=priority,
            order=next(self._order),
        )

        with self._lock:
            self._connections.append(
                connection
            )

            self._connections.sort(
                key=lambda item: (
                    -item.priority,
                    item.order,
                )
            )

        tracker = getattr(
            owner,
            "_track_signal_connection",
            None,
        )

        if tracker is not None:
            tracker(connection)

        return connection

    def connect_once(
        self,
        callback: Callable[..., Any],
        *,
        owner: object | None = None,
        priority: int = 0,
    ) -> SignalConnection:
        return self.connect(
            callback,
            owner=owner,
            once=True,
            priority=priority,
        )

    def disconnect(
        self,
        callback_or_connection,
    ) -> bool:
        if isinstance(
            callback_or_connection,
            SignalConnection,
        ):
            connection = (
                callback_or_connection
            )

            with self._lock:
                if connection not in self._connections:
                    return False

            self._disconnect_connection(
                connection
            )
            return True

        callback = callback_or_connection

        with self._lock:
            matches = [
                connection
                for connection in self._connections
                if self._callbacks_equal(
                    connection.callback,
                    callback,
                )
            ]

        for connection in matches:
            self._disconnect_connection(
                connection
            )

        return bool(matches)

    def is_connected(
        self,
        callback: Callable[..., Any],
    ) -> bool:
        with self._lock:
            return any(
                self._callbacks_equal(
                    connection.callback,
                    callback,
                )
                for connection in self._connections
                if connection.connected
            )

    def emit(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        with self._lock:
            connections = tuple(
                self._connections
            )

        stale: list[
            SignalConnection
        ] = []

        for connection in connections:
            if not connection.connected:
                continue

            if connection.blocked:
                continue

            callback = connection.callback

            if callback is None:
                stale.append(connection)
                continue

            try:
                callback(
                    *args,
                    **kwargs,
                )
            finally:
                if connection.once:
                    self._disconnect_connection(
                        connection
                    )

        for connection in stale:
            self._disconnect_connection(
                connection
            )

    def clear(self) -> None:
        with self._lock:
            connections = tuple(
                self._connections
            )

        for connection in connections:
            self._disconnect_connection(
                connection
            )

    def __len__(self) -> int:
        with self._lock:
            self._prune_dead_locked()
            return len(self._connections)

    def _disconnect_connection(
        self,
        connection: SignalConnection,
    ) -> None:
        owner = None

        with self._lock:
            if connection in self._connections:
                self._connections.remove(
                    connection
                )

            if not connection._connected:
                return

            connection._connected = False
            owner = connection.owner

        untracker = getattr(
            owner,
            "_untrack_signal_connection",
            None,
        )

        if untracker is not None:
            untracker(connection)

    def _prune_dead_locked(self) -> None:
        dead = [
            connection
            for connection in self._connections
            if connection.callback is None
        ]

        for connection in dead:
            self._connections.remove(
                connection
            )
            connection._connected = False

    @staticmethod
    def _callbacks_equal(
        left: Callable[..., Any] | None,
        right: Callable[..., Any] | None,
    ) -> bool:
        if left is right:
            return True

        if left is None or right is None:
            return False

        left_self = getattr(
            left,
            "__self__",
            None,
        )
        right_self = getattr(
            right,
            "__self__",
            None,
        )

        left_func = getattr(
            left,
            "__func__",
            None,
        )
        right_func = getattr(
            right,
            "__func__",
            None,
        )

        return (
            left_self is not None
            and left_self is right_self
            and left_func is right_func
        )
