from __future__ import annotations

from collections.abc import Callable

from nexora.data.save.events import SaveEvent


SaveEventListener = Callable[[SaveEvent], None]


class SaveEventDispatcher:
    """Small isolated dispatcher used by :class:`SaveManager`.

    Listener failures are intentionally swallowed so notifications can never
    make a save/load/delete operation fail.
    """

    def __init__(self) -> None:
        self._listeners: list[SaveEventListener] = []

    @property
    def listeners(self) -> tuple[SaveEventListener, ...]:
        return tuple(self._listeners)

    def add(self, callback: SaveEventListener) -> None:
        if not callable(callback):
            raise TypeError("Save event listener must be callable.")
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove(self, callback: SaveEventListener) -> bool:
        try:
            self._listeners.remove(callback)
        except ValueError:
            return False
        return True

    def clear(self) -> None:
        self._listeners.clear()

    def emit(self, event: SaveEvent) -> None:
        for callback in tuple(self._listeners):
            try:
                callback(event)
            except Exception:
                continue
