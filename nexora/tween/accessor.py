from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class PropertyAccessor:
    target: object
    path: str

    def __post_init__(self) -> None:
        self.path = str(self.path).strip()
        if not self.path:
            raise ValueError("Tween property path cannot be empty.")

    def _resolve_parent(self) -> tuple[object, str]:
        parts = self.path.split(".")
        current: Any = self.target
        for part in parts[:-1]:
            current = getattr(current, part)
        return current, parts[-1]

    def get(self):
        parent, attribute = self._resolve_parent()
        return getattr(parent, attribute)

    def set(self, value) -> None:
        parent, attribute = self._resolve_parent()
        setattr(parent, attribute, value)
