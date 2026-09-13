from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class AnimationFrame:
    """
    One frame of an animation.

    index:
        Logical frame index inside a sprite sheet.

    duration:
        Frame duration in seconds.

    uv:
        Nexora sprite UV region:

            (
                uv_x,
                uv_y,
                uv_width,
                uv_height,
            )

        All values are normalized to the texture size.
    """

    index: int

    duration: float

    uv: tuple[
        float,
        float,
        float,
        float,
    ] | None = None

    def __post_init__(
        self,
    ) -> None:
        if self.index < 0:
            raise ValueError(
                "AnimationFrame index must be >= 0."
            )

        if self.duration <= 0.0:
            raise ValueError(
                "AnimationFrame duration must be > 0."
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AnimationClip:
    """
    Immutable animation definition.

    Animation clips can be created manually or generated from
    regular sprite-sheet grids.
    """

    name: str

    frames: tuple[
        AnimationFrame,
        ...,
    ]

    loop: bool = True

    def __post_init__(
        self,
    ) -> None:
        if not self.name:
            raise ValueError(
                "AnimationClip name cannot be empty."
            )

        if not self.frames:
            raise ValueError(
                "AnimationClip must contain at least one frame."
            )

    # ==============================================================
    # Properties
    # ==============================================================

    @property
    def duration(
        self,
    ) -> float:
        """
        Total animation duration in seconds.
        """

        return sum(
            frame.duration
            for frame in self.frames
        )

    @property
    def frame_count(
        self,
    ) -> int:
        """
        Number of frames in this animation.
        """

        return len(
            self.frames
        )

    # ==============================================================
    # Grid creation
    # ==============================================================

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
    ) -> AnimationClip:
        """
        Create an animation from sequential cells in a sprite sheet.

        Frame indexing is row-major.

        Example grid with 4 columns:

            0   1   2   3
            4   5   6   7
            8   9  10  11

        The animation is allowed to span multiple rows.

        Example:

            AnimationClip.from_grid(
                "explosion",
                start_frame=3,
                frame_count=7,
                columns=4,
                rows=4,
                fps=16.0,
                loop=False,
            )
        """

        cls._validate_grid(
            start_frame=start_frame,
            frame_count=frame_count,
            columns=columns,
            rows=rows,
            fps=fps,
        )

        total_frames = (
            columns
            * rows
        )

        end_frame = (
            start_frame
            + frame_count
        )

        if end_frame > total_frames:
            raise ValueError(
                "Animation frame range exceeds "
                "the sprite-sheet grid."
            )

        frame_duration = (
            1.0
            / float(fps)
        )

        frames: list[
            AnimationFrame
        ] = []

        for frame_index in range(
            start_frame,
            end_frame,
        ):
            uv = cls._frame_uv(
                frame_index=frame_index,
                columns=columns,
                rows=rows,
            )

            frames.append(
                AnimationFrame(
                    index=frame_index,
                    duration=frame_duration,
                    uv=uv,
                )
            )

        return cls(
            name=name,
            frames=tuple(
                frames
            ),
            loop=loop,
        )

    # ==============================================================
    # Row creation
    # ==============================================================

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
    ) -> AnimationClip:
        """
        Create an animation from a single sprite-sheet row.

        Unlike from_grid(), this method never crosses into the next
        row.

        Example:

            AnimationClip.from_row(
                "walk_right",
                row=2,
                start_column=1,
                frame_count=7,
                columns=10,
                rows=8,
                fps=12.0,
            )
        """

        if columns <= 0:
            raise ValueError(
                "columns must be greater than zero."
            )

        if rows <= 0:
            raise ValueError(
                "rows must be greater than zero."
            )

        if row < 0:
            raise ValueError(
                "row must be >= 0."
            )

        if row >= rows:
            raise ValueError(
                "row is outside the sprite-sheet grid."
            )

        if start_column < 0:
            raise ValueError(
                "start_column must be >= 0."
            )

        if start_column >= columns:
            raise ValueError(
                "start_column is outside "
                "the sprite-sheet grid."
            )

        if frame_count <= 0:
            raise ValueError(
                "frame_count must be greater than zero."
            )

        if (
            start_column
            + frame_count
            > columns
        ):
            raise ValueError(
                "Animation row range exceeds "
                "the available columns."
            )

        if fps <= 0.0:
            raise ValueError(
                "fps must be greater than zero."
            )

        start_frame = (
            row
            * columns
            + start_column
        )

        return cls.from_grid(
            name,
            start_frame=start_frame,
            frame_count=frame_count,
            columns=columns,
            rows=rows,
            fps=fps,
            loop=loop,
        )

    # ==============================================================
    # Validation
    # ==============================================================

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
            raise ValueError(
                "columns must be greater than zero."
            )

        if rows <= 0:
            raise ValueError(
                "rows must be greater than zero."
            )

        if start_frame < 0:
            raise ValueError(
                "start_frame must be >= 0."
            )

        if frame_count <= 0:
            raise ValueError(
                "frame_count must be greater than zero."
            )

        if fps <= 0.0:
            raise ValueError(
                "fps must be greater than zero."
            )

        total_frames = (
            columns
            * rows
        )

        if start_frame >= total_frames:
            raise ValueError(
                "start_frame is outside "
                "the sprite-sheet grid."
            )

    # ==============================================================
    # UV calculation
    # ==============================================================

    @staticmethod
    def _frame_uv(
        *,
        frame_index: int,
        columns: int,
        rows: int,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        """
        Convert a grid frame index into Nexora's sprite UV format.

        Nexora uses:

            (
                uv_x,
                uv_y,
                uv_width,
                uv_height,
            )

        rather than:

            (
                u0,
                v0,
                u1,
                v1,
            )

        Example:

            columns = 4
            rows = 2
            frame_index = 5

        Frame 5 is:

            column = 1
            row = 1

        Result:

            (
                0.25,
                0.5,
                0.25,
                0.5,
            )
        """

        column = (
            frame_index
            % columns
        )

        row = (
            frame_index
            // columns
        )

        cell_width = (
            1.0
            / float(columns)
        )

        cell_height = (
            1.0
            / float(rows)
        )

        uv_x = (
            column
            * cell_width
        )

        uv_y = (
            row
            * cell_height
        )

        return (
            uv_x,
            uv_y,
            cell_width,
            cell_height,
        )