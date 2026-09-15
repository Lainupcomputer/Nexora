from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True, slots=True)
class AnimationFrame:
    index: int
    duration: float
    uv: tuple[float, float, float, float] | None = None

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("AnimationFrame index must be >= 0.")
        if self.duration <= 0.0:
            raise ValueError("AnimationFrame duration must be > 0.")


@dataclass(frozen=True, slots=True)
class AnimationEvent:
    """Named event emitted when an animation enters ``frame``."""

    frame: int
    name: str
    data: Any = None

    def __post_init__(self) -> None:
        if self.frame < 0:
            raise ValueError("AnimationEvent frame must be >= 0.")
        if not self.name:
            raise ValueError("AnimationEvent name cannot be empty.")


@dataclass(frozen=True, slots=True)
class AnimationClip:
    name: str
    frames: tuple[AnimationFrame, ...]
    loop: bool = True
    events: tuple[AnimationEvent, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("AnimationClip name cannot be empty.")
        if not self.frames:
            raise ValueError("AnimationClip must contain at least one frame.")
        for event in self.events:
            if event.frame >= len(self.frames):
                raise ValueError(
                    f"Animation event {event.name!r} references frame "
                    f"{event.frame}, but clip {self.name!r} only has "
                    f"{len(self.frames)} frames."
                )

    @property
    def duration(self) -> float:
        return sum(frame.duration for frame in self.frames)

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    def events_for_frame(self, frame: int) -> tuple[AnimationEvent, ...]:
        return tuple(event for event in self.events if event.frame == frame)

    def with_event(
        self,
        frame: int,
        name: str,
        data: Any = None,
    ) -> AnimationClip:
        """Return a copy with one additional frame event."""
        return replace(
            self,
            events=self.events + (AnimationEvent(frame, name, data),),
        )

    @classmethod
    def from_grid(
        cls,
        name: str,
        *,
        start_frame: int,
        frame_count: int,
        columns: int,
        rows: int,
        fps: float,
        loop: bool = True,
        events: tuple[AnimationEvent, ...] = (),
    ) -> AnimationClip:
        cls._validate_grid(
            start_frame=start_frame,
            frame_count=frame_count,
            columns=columns,
            rows=rows,
            fps=fps,
        )
        total_frames = columns * rows
        end_frame = start_frame + frame_count
        if end_frame > total_frames:
            raise ValueError("Animation frame range exceeds the sprite-sheet grid.")
        frame_duration = 1.0 / float(fps)
        frames = tuple(
            AnimationFrame(
                index=frame_index,
                duration=frame_duration,
                uv=cls._frame_uv(
                    frame_index=frame_index,
                    columns=columns,
                    rows=rows,
                ),
            )
            for frame_index in range(start_frame, end_frame)
        )
        return cls(name=name, frames=frames, loop=loop, events=events)

    @classmethod
    def from_row(
        cls,
        name: str,
        *,
        row: int,
        frame_count: int,
        columns: int,
        rows: int,
        fps: float,
        start_column: int = 0,
        loop: bool = True,
        events: tuple[AnimationEvent, ...] = (),
    ) -> AnimationClip:
        if columns <= 0:
            raise ValueError("columns must be greater than zero.")
        if rows <= 0:
            raise ValueError("rows must be greater than zero.")
        if row < 0 or row >= rows:
            raise ValueError("row is outside the sprite-sheet grid.")
        if start_column < 0 or start_column >= columns:
            raise ValueError("start_column is outside the sprite-sheet grid.")
        if frame_count <= 0:
            raise ValueError("frame_count must be greater than zero.")
        if start_column + frame_count > columns:
            raise ValueError("Animation row range exceeds the available columns.")
        if fps <= 0.0:
            raise ValueError("fps must be greater than zero.")
        return cls.from_grid(
            name,
            start_frame=row * columns + start_column,
            frame_count=frame_count,
            columns=columns,
            rows=rows,
            fps=fps,
            loop=loop,
            events=events,
        )

    @staticmethod
    def _validate_grid(
        *,
        start_frame: int,
        frame_count: int,
        columns: int,
        rows: int,
        fps: float,
    ) -> None:
        if columns <= 0:
            raise ValueError("columns must be greater than zero.")
        if rows <= 0:
            raise ValueError("rows must be greater than zero.")
        if start_frame < 0:
            raise ValueError("start_frame must be >= 0.")
        if frame_count <= 0:
            raise ValueError("frame_count must be greater than zero.")
        if fps <= 0.0:
            raise ValueError("fps must be greater than zero.")
        if start_frame >= columns * rows:
            raise ValueError("start_frame is outside the sprite-sheet grid.")

    @staticmethod
    def _frame_uv(
        *,
        frame_index: int,
        columns: int,
        rows: int,
    ) -> tuple[float, float, float, float]:
        column = frame_index % columns
        row = frame_index // columns
        cell_width = 1.0 / float(columns)
        cell_height = 1.0 / float(rows)
        return (
            column * cell_width,
            row * cell_height,
            cell_width,
            cell_height,
        )
