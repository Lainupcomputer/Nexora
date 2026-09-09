from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Entity:
    """
    Lightweight identifier for an ECS entity.
    """

    id: int

    def __int__(self) -> int:
        return self.id