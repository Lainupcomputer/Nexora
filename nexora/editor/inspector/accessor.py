from __future__ import annotations


class PropertyPathAccessor:
    """
    Read and write dotted attribute paths.

    Example:
        transform.x
        velocity.y
        name
    """

    def __init__(
        self,
        target,
        path: str,
    ) -> None:
        self.target = target
        self.path = str(
            path
        )

        self.parts = [
            part
            for part in self.path.split(".")
            if part
        ]

        if not self.parts:
            raise ValueError(
                "Property path cannot be empty."
            )

    def _resolve_parent(
        self,
    ):
        obj = self.target

        for part in self.parts[:-1]:
            obj = getattr(
                obj,
                part,
            )

        return obj

    def get(
        self,
    ):
        obj = self.target

        for part in self.parts:
            obj = getattr(
                obj,
                part,
            )

        return obj

    def set(
        self,
        value,
    ) -> None:
        parent = (
            self._resolve_parent()
        )

        setattr(
            parent,
            self.parts[-1],
            value,
        )