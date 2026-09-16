from __future__ import annotations

from typing import Protocol


class EditorCommand(Protocol):
    label: str

    def execute(self): ...
    def undo(self): ...


class CommandStack:
    """Small undo/redo stack used by the Nexora editor."""

    def __init__(self, *, max_history: int = 200) -> None:
        self.max_history = max(1, int(max_history))
        self._undo: list[EditorCommand] = []
        self._redo: list[EditorCommand] = []

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def undo_label(self) -> str | None:
        return self._undo[-1].label if self._undo else None

    @property
    def redo_label(self) -> str | None:
        return self._redo[-1].label if self._redo else None

    def execute(self, command: EditorCommand):
        result = command.execute()
        self._undo.append(command)
        self._redo.clear()
        if len(self._undo) > self.max_history:
            del self._undo[0 : len(self._undo) - self.max_history]
        return result

    def undo(self):
        if not self._undo:
            return None
        command = self._undo.pop()
        result = command.undo()
        self._redo.append(command)
        return result

    def redo(self):
        if not self._redo:
            return None
        command = self._redo.pop()
        result = command.execute()
        self._undo.append(command)
        return result

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
