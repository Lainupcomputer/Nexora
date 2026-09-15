from __future__ import annotations

from dataclasses import dataclass


Point2 = tuple[float, float]


@dataclass(slots=True, frozen=True)
class OccluderSnapshot:
    """Immutable world-space polygon submitted by LightOccluder2D."""

    points: tuple[Point2, ...]
    mask: int = 0xFFFFFFFF
    closed: bool = True

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("An occluder requires at least two points")

    def segments(self) -> tuple[tuple[Point2, Point2], ...]:
        result: list[tuple[Point2, Point2]] = []
        for index in range(len(self.points) - 1):
            result.append((self.points[index], self.points[index + 1]))
        if self.closed and len(self.points) >= 3:
            result.append((self.points[-1], self.points[0]))
        return tuple(result)
