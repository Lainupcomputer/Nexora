from __future__ import annotations

from nexora.signals import Signal


class SelectionService:
    """Central editor selection shared by tree, viewport and inspector."""

    def __init__(self) -> None:
        self.changed = Signal("editor.selection.changed")
        self._selected = None

    @property
    def selected(self):
        return self._selected

    def select(self, value) -> bool:
        if value is self._selected:
            return False

        previous = self._selected
        self._selected = value
        self.changed.emit(value, previous)
        return True

    def clear(self) -> bool:
        return self.select(None)
