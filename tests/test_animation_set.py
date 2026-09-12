from __future__ import annotations

import pytest

from nexora.animation import (
    AnimationClip,
    AnimationSet,
)



# ==============================================================
# Helpers
# ==============================================================


def create_set() -> AnimationSet:
    return AnimationSet(
        columns=8,
        rows=4,
    )


def create_clip(
    name: str = "walk",
) -> AnimationClip:
    return AnimationClip.from_row(
        name,
        row=0,
        frame_count=4,
        columns=8,
        rows=4,
        fps=10.0,
    )


# ==============================================================
# Construction
# ==============================================================


def test_animation_set_stores_grid_size():
    animations = AnimationSet(
        columns=12,
        rows=6,
    )

    assert animations.columns == 12
    assert animations.rows == 6


def test_animation_set_rejects_zero_columns():
    with pytest.raises(
        ValueError
    ):
        AnimationSet(
            columns=0,
            rows=4,
        )


def test_animation_set_rejects_negative_columns():
    with pytest.raises(
        ValueError
    ):
        AnimationSet(
            columns=-1,
            rows=4,
        )


def test_animation_set_rejects_zero_rows():
    with pytest.raises(
        ValueError
    ):
        AnimationSet(
            columns=4,
            rows=0,
        )


def test_animation_set_rejects_negative_rows():
    with pytest.raises(
        ValueError
    ):
        AnimationSet(
            columns=4,
            rows=-1,
        )


# ==============================================================
# Add / get
# ==============================================================


def test_add_clip():
    animations = create_set()

    clip = create_clip()

    result = animations.add(
        clip
    )

    assert result is clip
    assert animations.has(
        "walk"
    )

    assert animations.get(
        "walk"
    ) is clip


def test_add_duplicate_raises():
    animations = create_set()

    animations.add(
        create_clip()
    )

    with pytest.raises(
        ValueError
    ):
        animations.add(
            create_clip()
        )


def test_add_duplicate_can_replace():
    animations = create_set()

    first = create_clip()

    second = AnimationClip.from_row(
        "walk",
        row=1,
        frame_count=3,
        columns=8,
        rows=4,
        fps=12.0,
    )

    animations.add(
        first
    )

    animations.add(
        second,
        replace=True,
    )

    assert animations.get(
        "walk"
    ) is second


# ==============================================================
# Get / require
# ==============================================================


def test_get_missing_returns_none():
    animations = create_set()

    assert animations.get(
        "missing"
    ) is None


def test_require_returns_clip():
    animations = create_set()

    clip = create_clip()

    animations.add(
        clip
    )

    assert animations.require(
        "walk"
    ) is clip


def test_require_missing_raises():
    animations = create_set()

    with pytest.raises(
        KeyError
    ):
        animations.require(
            "missing"
        )


# ==============================================================
# Remove
# ==============================================================


def test_remove_clip():
    animations = create_set()

    clip = create_clip()

    animations.add(
        clip
    )

    removed = animations.remove(
        "walk"
    )

    assert removed is clip

    assert not animations.has(
        "walk"
    )


def test_remove_missing_returns_none():
    animations = create_set()

    assert animations.remove(
        "missing"
    ) is None


# ==============================================================
# Clear
# ==============================================================


def test_clear():
    animations = create_set()

    animations.add(
        create_clip(
            "idle"
        )
    )

    animations.add(
        create_clip(
            "walk"
        )
    )

    assert len(
        animations
    ) == 2

    animations.clear()

    assert len(
        animations
    ) == 0


# ==============================================================
# add_row
# ==============================================================


def test_add_row_creates_clip():
    animations = create_set()

    clip = animations.add_row(
        "walk",
        row=2,
        frame_count=4,
        fps=12.0,
    )

    assert animations.has(
        "walk"
    )

    assert clip.name == "walk"
    assert clip.frame_count == 4


def test_add_row_uses_set_grid_dimensions():
    animations = AnimationSet(
        columns=8,
        rows=4,
    )

    clip = animations.add_row(
        "walk",
        row=1,
        frame_count=3,
        fps=10.0,
    )

    assert [
        frame.index
        for frame in clip.frames
    ] == [
        8,
        9,
        10,
    ]


def test_add_row_supports_start_column():
    animations = create_set()

    clip = animations.add_row(
        "attack",
        row=1,
        start_column=3,
        frame_count=3,
        fps=10.0,
    )

    assert [
        frame.index
        for frame in clip.frames
    ] == [
        11,
        12,
        13,
    ]


def test_add_row_preserves_loop_flag():
    animations = create_set()

    clip = animations.add_row(
        "attack",
        row=0,
        frame_count=4,
        fps=12.0,
        loop=False,
    )

    assert clip.loop is False


def test_add_row_duplicate_raises():
    animations = create_set()

    animations.add_row(
        "walk",
        row=0,
        frame_count=4,
        fps=10.0,
    )

    with pytest.raises(
        ValueError
    ):
        animations.add_row(
            "walk",
            row=1,
            frame_count=4,
            fps=10.0,
        )


def test_add_row_duplicate_can_replace():
    animations = create_set()

    first = animations.add_row(
        "walk",
        row=0,
        frame_count=4,
        fps=10.0,
    )

    second = animations.add_row(
        "walk",
        row=1,
        frame_count=3,
        fps=12.0,
        replace=True,
    )

    assert first is not second

    assert animations.get(
        "walk"
    ) is second


# ==============================================================
# add_grid
# ==============================================================


def test_add_grid_creates_clip():
    animations = create_set()

    clip = animations.add_grid(
        "effect",
        start_frame=5,
        frame_count=6,
        fps=20.0,
    )

    assert animations.has(
        "effect"
    )

    assert clip.frame_count == 6


def test_add_grid_can_cross_rows():
    animations = AnimationSet(
        columns=4,
        rows=3,
    )

    clip = animations.add_grid(
        "effect",
        start_frame=2,
        frame_count=5,
        fps=10.0,
    )

    assert [
        frame.index
        for frame in clip.frames
    ] == [
        2,
        3,
        4,
        5,
        6,
    ]


def test_add_grid_preserves_loop_flag():
    animations = create_set()

    clip = animations.add_grid(
        "explosion",
        start_frame=0,
        frame_count=4,
        fps=12.0,
        loop=False,
    )

    assert clip.loop is False


# ==============================================================
# Collection API
# ==============================================================


def test_names():
    animations = create_set()

    animations.add(
        create_clip(
            "idle"
        )
    )

    animations.add(
        create_clip(
            "walk"
        )
    )

    assert animations.names == (
        "idle",
        "walk",
    )


def test_clips():
    animations = create_set()

    idle = create_clip(
        "idle"
    )

    walk = create_clip(
        "walk"
    )

    animations.add(
        idle
    )

    animations.add(
        walk
    )

    assert animations.clips == (
        idle,
        walk,
    )


def test_len():
    animations = create_set()

    assert len(
        animations
    ) == 0

    animations.add(
        create_clip(
            "idle"
        )
    )

    assert len(
        animations
    ) == 1

    animations.add(
        create_clip(
            "walk"
        )
    )

    assert len(
        animations
    ) == 2


def test_contains():
    animations = create_set()

    animations.add(
        create_clip()
    )

    assert "walk" in animations
    assert "missing" not in animations


def test_iteration():
    animations = create_set()

    idle = create_clip(
        "idle"
    )

    walk = create_clip(
        "walk"
    )

    animations.add(
        idle
    )

    animations.add(
        walk
    )

    assert list(
        animations
    ) == [
        idle,
        walk,
    ]


# ==============================================================
# AnimatedSprite integration expectation
# ==============================================================


def test_animation_set_can_supply_multiple_clips():
    animations = AnimationSet(
        columns=8,
        rows=4,
    )

    animations.add_row(
        "idle_down",
        row=0,
        frame_count=4,
        fps=6.0,
    )

    animations.add_row(
        "walk_down",
        row=1,
        frame_count=6,
        fps=12.0,
    )

    animations.add_row(
        "roll_down",
        row=2,
        frame_count=5,
        fps=16.0,
        loop=False,
    )

    assert animations.names == (
        "idle_down",
        "walk_down",
        "roll_down",
    )

    assert animations.require(
        "idle_down"
    ).frame_count == 4

    assert animations.require(
        "walk_down"
    ).frame_count == 6

    assert animations.require(
        "roll_down"
    ).frame_count == 5

    assert animations.require(
        "roll_down"
    ).loop is False