from __future__ import annotations

from collections.abc import Iterator

from nexora.animation.clip import AnimationClip

class AnimationSet:
    """
    Collection of animation clips that belong to the same
    sprite sheet.

    AnimationSet stores the sprite-sheet grid dimensions and
    provides convenience methods for creating animations from
    rows or arbitrary grid positions.

    It does not own a texture and is independent from rendering.
    """

    def __init__(
        self,
        *,
        columns: int,
        rows: int,
    ) -> None:
        if columns <= 0:
            raise ValueError(
                "columns must be greater than zero."
            )

        if rows <= 0:
            raise ValueError(
                "rows must be greater than zero."
            )

        self.columns = int(
            columns
        )

        self.rows = int(
            rows
        )

        self._clips: dict[
            str,
            AnimationClip,
        ] = {}

    # ==============================================================
    # Clips
    # ==============================================================

    def add(
        self,
        clip: AnimationClip,
        *,
        replace: bool = False,
    ) -> AnimationClip:
        """
        Add an existing AnimationClip.
        """

        if (
            clip.name in self._clips
            and not replace
        ):
            raise ValueError(
                f"Animation {clip.name!r} already exists."
            )

        self._clips[
            clip.name
        ] = clip

        return clip

    def remove(
        self,
        name: str,
    ) -> AnimationClip | None:
        """
        Remove and return an animation.
        """

        return self._clips.pop(
            name,
            None,
        )

    def get(
        self,
        name: str,
    ) -> AnimationClip | None:
        return self._clips.get(
            name
        )

    def require(
        self,
        name: str,
    ) -> AnimationClip:
        """
        Return an animation or raise KeyError.
        """

        clip = self.get(
            name
        )

        if clip is None:
            raise KeyError(
                f"Animation {name!r} does not exist."
            )

        return clip

    def has(
        self,
        name: str,
    ) -> bool:
        return name in self._clips

    def clear(
        self,
    ) -> None:
        self._clips.clear()

    # ==============================================================
    # Row animations
    # ==============================================================

    def add_row(
        self,
        name: str,
        *,
        row: int,
        frame_count: int,
        fps: float,
        start_column: int = 0,
        loop: bool = True,
        replace: bool = False,
    ) -> AnimationClip:
        """
        Create and add an animation from one sprite-sheet row.

        frame_count may be any valid number of frames.
        """

        clip = AnimationClip.from_row(
            name,
            row=row,
            start_column=start_column,
            frame_count=frame_count,
            columns=self.columns,
            rows=self.rows,
            fps=fps,
            loop=loop,
        )

        return self.add(
            clip,
            replace=replace,
        )

    # ==============================================================
    # Grid animations
    # ==============================================================

    def add_grid(
        self,
        name: str,
        *,
        start_frame: int,
        frame_count: int,
        fps: float,
        loop: bool = True,
        replace: bool = False,
    ) -> AnimationClip:
        """
        Create an animation from sequential cells in the
        complete sprite-sheet grid.

        Frames may continue onto the next row.
        """

        clip = AnimationClip.from_grid(
            name,
            start_frame=start_frame,
            frame_count=frame_count,
            columns=self.columns,
            rows=self.rows,
            fps=fps,
            loop=loop,
        )

        return self.add(
            clip,
            replace=replace,
        )

    # ==============================================================
    # Collection API
    # ==============================================================

    @property
    def clips(
        self,
    ) -> tuple[
        AnimationClip,
        ...,
    ]:
        return tuple(
            self._clips.values()
        )

    @property
    def names(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return tuple(
            self._clips.keys()
        )

    def __len__(
        self,
    ) -> int:
        return len(
            self._clips
        )

    def __contains__(
        self,
        name: object,
    ) -> bool:
        return name in self._clips

    def __iter__(
        self,
    ) -> Iterator[
        AnimationClip
    ]:
        return iter(
            self._clips.values()
        )