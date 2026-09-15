from __future__ import annotations

from enum import StrEnum


class TileProjection(StrEnum):
    """Supported TileMap coordinate projections."""

    ORTHOGONAL = "orthogonal"
    ISOMETRIC = "isometric"

    @classmethod
    def coerce(cls, value: "TileProjection | str") -> "TileProjection":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError as exc:
            raise ValueError(
                f"Unsupported tile projection: {value!r}. "
                f"Expected one of: {', '.join(item.value for item in cls)}"
            ) from exc
