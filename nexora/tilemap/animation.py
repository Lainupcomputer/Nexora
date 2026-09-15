from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TileAnimationFrame:
    tile_id: int
    duration: float

    def __post_init__(self) -> None:
        if int(self.tile_id) < 0:
            raise ValueError("tile_id must be >= 0")
        if float(self.duration) <= 0.0:
            raise ValueError("duration must be > 0")


class TileAnimation:
    """Looping tile animation stored by a TileSet."""

    def __init__(self, frames) -> None:
        normalized = tuple(
            frame if isinstance(frame, TileAnimationFrame)
            else TileAnimationFrame(int(frame[0]), float(frame[1]))
            for frame in frames
        )
        if not normalized:
            raise ValueError("TileAnimation requires at least one frame")
        self.frames = normalized
        self.duration = sum(frame.duration for frame in normalized)

    def tile_at(self, elapsed: float) -> int:
        if len(self.frames) == 1:
            return self.frames[0].tile_id
        time = float(elapsed) % self.duration
        cursor = 0.0
        for frame in self.frames:
            cursor += frame.duration
            if time < cursor:
                return frame.tile_id
        return self.frames[-1].tile_id

    def to_state(self) -> list[tuple[int, float]]:
        return [(frame.tile_id, frame.duration) for frame in self.frames]

    @classmethod
    def from_state(cls, state) -> "TileAnimation":
        return cls(state)
