from __future__ import annotations

from nexora.editor.inspector import (
    PropertyPathAccessor,
)


class SetPropertyCommand:
    """Undoable assignment of a dotted attribute path."""

    def __init__(
        self,
        target,
        path: str,
        value,
        *,
        label: str | None = None,
    ) -> None:
        self.target = target
        self.path = str(
            path
        )
        self.value = value

        self.accessor = (
            PropertyPathAccessor(
                target,
                self.path,
            )
        )

        self.previous = (
            self.accessor.get()
        )

        self.label = (
            label
            or f"Set {self.path}"
        )

    def execute(
        self,
    ):
        self.accessor.set(
            self.value
        )

        return self.target

    def undo(
        self,
    ):
        self.accessor.set(
            self.previous
        )

        return self.target