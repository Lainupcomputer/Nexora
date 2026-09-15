from __future__ import annotations


class CommandHistory:
    def __init__(self, max_entries: int = 100) -> None:
        self.max_entries = max(1, int(max_entries))
        self._items: list[str] = []
        self._cursor: int | None = None
        self._draft = ""

    @property
    def items(self) -> tuple[str, ...]:
        return tuple(self._items)

    def add(self, command: str) -> None:
        command = str(command).strip()

        if not command:
            return

        if not self._items or self._items[-1] != command:
            self._items.append(command)

        if len(self._items) > self.max_entries:
            del self._items[: len(self._items) - self.max_entries]

        self.reset_navigation()

    def reset_navigation(self) -> None:
        self._cursor = None
        self._draft = ""

    def previous(self, current: str) -> str:
        if not self._items:
            return current

        if self._cursor is None:
            self._draft = current
            self._cursor = len(self._items) - 1
        else:
            self._cursor = max(0, self._cursor - 1)

        return self._items[self._cursor]

    def next(self, current: str) -> str:
        if self._cursor is None:
            return current

        self._cursor += 1

        if self._cursor >= len(self._items):
            draft = self._draft
            self.reset_navigation()
            return draft

        return self._items[self._cursor]
