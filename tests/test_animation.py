from __future__ import annotations

import pytest

from nexora.animation import (
    AnimationClip,
    AnimationFrame,
    Animator,
)


# ==============================================================
# AnimationFrame
# ==============================================================


def test_animation_frame_accepts_valid_data():
    frame = AnimationFrame(
        index=0,
        duration=0.1,
        uv=(
            0.0,
            0.0,
            0.5,
            0.5,
        ),
    )

    assert frame.index == 0
    assert frame.duration == pytest.approx(
        0.1
    )

    assert frame.uv == pytest.approx(
        (
            0.0,
            0.0,
            0.5,
            0.5,
        )
    )


def test_animation_frame_rejects_negative_index():
    with pytest.raises(
        ValueError
    ):
        AnimationFrame(
            index=-1,
            duration=0.1,
        )


def test_animation_frame_rejects_zero_duration():
    with pytest.raises(
        ValueError
    ):
        AnimationFrame(
            index=0,
            duration=0.0,
        )


def test_animation_frame_rejects_negative_duration():
    with pytest.raises(
        ValueError
    ):
        AnimationFrame(
            index=0,
            duration=-0.1,
        )


# ==============================================================
# AnimationClip
# ==============================================================


def test_animation_clip_properties():
    clip = AnimationClip(
        name="walk",
        frames=(
            AnimationFrame(
                index=0,
                duration=0.1,
            ),
            AnimationFrame(
                index=1,
                duration=0.2,
            ),
            AnimationFrame(
                index=2,
                duration=0.3,
            ),
        ),
    )

    assert clip.name == "walk"

    assert clip.frame_count == 3

    assert clip.duration == pytest.approx(
        0.6
    )


def test_animation_clip_rejects_empty_name():
    with pytest.raises(
        ValueError
    ):
        AnimationClip(
            name="",
            frames=(
                AnimationFrame(
                    index=0,
                    duration=0.1,
                ),
            ),
        )


def test_animation_clip_rejects_empty_frames():
    with pytest.raises(
        ValueError
    ):
        AnimationClip(
            name="empty",
            frames=(),
        )


# ==============================================================
# Animator clips
# ==============================================================


def create_test_clip(
    name: str = "walk",
    *,
    loop: bool = True,
) -> AnimationClip:
    return AnimationClip(
        name=name,
        frames=(
            AnimationFrame(
                index=0,
                duration=0.1,
            ),
            AnimationFrame(
                index=1,
                duration=0.1,
            ),
            AnimationFrame(
                index=2,
                duration=0.1,
            ),
        ),
        loop=loop,
    )


def test_animator_add_and_get_clip():
    animator = Animator()

    clip = create_test_clip()

    animator.add_clip(
        clip
    )

    assert animator.has_clip(
        "walk"
    )

    assert animator.get_clip(
        "walk"
    ) is clip


def test_animator_missing_clip_returns_none():
    animator = Animator()

    assert animator.get_clip(
        "missing"
    ) is None


def test_animator_remove_clip():
    animator = Animator()

    clip = create_test_clip()

    animator.add_clip(
        clip
    )

    animator.remove_clip(
        "walk"
    )

    assert not animator.has_clip(
        "walk"
    )


# ==============================================================
# Play
# ==============================================================


def test_animator_play_sets_initial_state():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    animator.play(
        "walk"
    )

    assert animator.playing
    assert not animator.finished

    assert animator.current_clip is not None

    assert animator.current_clip.name == (
        "walk"
    )

    assert animator.frame_index == 0

    assert animator.current_frame is not None

    assert animator.current_frame.index == 0


def test_animator_play_unknown_clip_raises():
    animator = Animator()

    with pytest.raises(
        KeyError
    ):
        animator.play(
            "missing"
        )


# ==============================================================
# Frame advancement
# ==============================================================


def test_animator_advances_one_frame():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    animator.play(
        "walk"
    )

    animator.update(
        0.1
    )

    assert animator.frame_index == 1

    assert animator.current_frame is not None

    assert animator.current_frame.index == 1


def test_animator_does_not_advance_too_early():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    animator.play(
        "walk"
    )

    animator.update(
        0.05
    )

    assert animator.frame_index == 0


def test_animator_can_skip_multiple_frames():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    animator.play(
        "walk"
    )

    animator.update(
        0.25
    )

    assert animator.frame_index == 2


def test_animator_keeps_remaining_frame_time():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    animator.play(
        "walk"
    )

    animator.update(
        0.15
    )

    assert animator.frame_index == 1

    animator.update(
        0.04
    )

    assert animator.frame_index == 1

    animator.update(
        0.01
    )

    assert animator.frame_index == 2


# ==============================================================
# Looping
# ==============================================================


def test_looping_animation_wraps_to_first_frame():
    animator = Animator()

    animator.add_clip(
        create_test_clip(
            loop=True
        )
    )

    animator.play(
        "walk"
    )

    animator.update(
        0.3
    )

    assert animator.playing
    assert not animator.finished

    assert animator.frame_index == 0


def test_looping_animation_can_wrap_multiple_times():
    animator = Animator()

    animator.add_clip(
        create_test_clip(
            loop=True
        )
    )

    animator.play(
        "walk"
    )

    animator.update(
        0.7
    )

    # total duration = 0.3
    #
    # 0.7:
    # 2 complete loops + 0.1
    #
    # therefore frame 1

    assert animator.frame_index == 1


# ==============================================================
# Non looping
# ==============================================================


def test_non_looping_animation_finishes():
    animator = Animator()

    animator.add_clip(
        create_test_clip(
            loop=False
        )
    )

    animator.play(
        "walk"
    )

    animator.update(
        0.3
    )

    assert not animator.playing
    assert animator.finished

    assert animator.frame_index == 2


def test_finished_animation_stays_on_last_frame():
    animator = Animator()

    animator.add_clip(
        create_test_clip(
            loop=False
        )
    )

    animator.play(
        "walk"
    )

    animator.update(
        1.0
    )

    assert animator.frame_index == 2

    animator.update(
        10.0
    )

    assert animator.frame_index == 2


# ==============================================================
# Pause / resume
# ==============================================================


def test_pause_prevents_update():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    animator.play(
        "walk"
    )

    animator.pause()

    animator.update(
        1.0
    )

    assert animator.frame_index == 0


def test_resume_continues_animation():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    animator.play(
        "walk"
    )

    animator.pause()

    animator.update(
        1.0
    )

    animator.resume()

    animator.update(
        0.1
    )

    assert animator.frame_index == 1


# ==============================================================
# Stop
# ==============================================================


def test_stop_clears_current_clip():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    animator.play(
        "walk"
    )

    animator.stop()

    assert animator.current_clip is None
    assert animator.current_frame is None

    assert animator.frame_index == 0

    assert not animator.playing
    assert not animator.finished


# ==============================================================
# Restart
# ==============================================================


def test_play_same_clip_without_restart_keeps_position():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    animator.play(
        "walk"
    )

    animator.update(
        0.1
    )

    assert animator.frame_index == 1

    animator.play(
        "walk"
    )

    assert animator.frame_index == 1


def test_play_same_clip_with_restart_resets_position():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    animator.play(
        "walk"
    )

    animator.update(
        0.1
    )

    assert animator.frame_index == 1

    animator.play(
        "walk",
        restart=True,
    )

    assert animator.frame_index == 0


# ==============================================================
# Speed
# ==============================================================


def test_animator_speed_multiplier():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    animator.speed = 2.0

    animator.play(
        "walk"
    )

    animator.update(
        0.05
    )

    assert animator.frame_index == 1


def test_zero_speed_freezes_animation():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    animator.speed = 0.0

    animator.play(
        "walk"
    )

    animator.update(
        10.0
    )

    assert animator.frame_index == 0


def test_negative_speed_is_treated_as_zero():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    animator.speed = -5.0

    animator.play(
        "walk"
    )

    animator.update(
        10.0
    )

    assert animator.frame_index == 0


# ==============================================================
# Events
# ==============================================================


def test_frame_changed_callback():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    frames: list[int] = []

    animator.on_frame_changed = (
        lambda frame:
        frames.append(
            frame.index
        )
    )

    animator.play(
        "walk"
    )

    animator.update(
        0.1
    )

    animator.update(
        0.1
    )

    assert frames == [
        0,
        1,
        2,
    ]


def test_finished_callback():
    animator = Animator()

    clip = create_test_clip(
        loop=False
    )

    animator.add_clip(
        clip
    )

    finished: list[str] = []

    animator.on_finished = (
        lambda current:
        finished.append(
            current.name
        )
    )

    animator.play(
        "walk"
    )

    animator.update(
        0.3
    )

    assert finished == [
        "walk"
    ]


def test_finished_callback_runs_once():
    animator = Animator()

    animator.add_clip(
        create_test_clip(
            loop=False
        )
    )

    count = 0

    def on_finished(
        clip: AnimationClip,
    ) -> None:
        nonlocal count
        count += 1

    animator.on_finished = (
        on_finished
    )

    animator.play(
        "walk"
    )

    animator.update(
        1.0
    )

    animator.update(
        1.0
    )

    animator.update(
        1.0
    )

    assert count == 1


# ==============================================================
# Reset
# ==============================================================


def test_reset_returns_to_first_frame():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    animator.play(
        "walk"
    )

    animator.update(
        0.2
    )

    assert animator.frame_index == 2

    animator.reset()

    assert animator.frame_index == 0
    assert not animator.finished


# ==============================================================
# Progress
# ==============================================================


def test_progress_without_clip_is_zero():
    animator = Animator()

    assert animator.progress == pytest.approx(
        0.0
    )


def test_animation_progress():
    animator = Animator()

    animator.add_clip(
        create_test_clip()
    )

    animator.play(
        "walk"
    )

    animator.update(
        0.15
    )

    # total = 0.3
    #
    # elapsed = 0.15

    assert animator.progress == pytest.approx(
        0.5
    )

# ==============================================================
# AnimationClip.from_grid
# ==============================================================


def test_from_grid_creates_correct_frame_count():
    clip = AnimationClip.from_grid(
        "walk",
        start_frame=0,
        frame_count=6,
        columns=8,
        rows=4,
        fps=12.0,
    )

    assert clip.frame_count == 6


def test_from_grid_sets_correct_indices():
    clip = AnimationClip.from_grid(
        "walk",
        start_frame=5,
        frame_count=4,
        columns=8,
        rows=4,
        fps=12.0,
    )

    indices = [
        frame.index
        for frame in clip.frames
    ]

    assert indices == [
        5,
        6,
        7,
        8,
    ]


def test_from_grid_sets_frame_duration_from_fps():
    clip = AnimationClip.from_grid(
        "walk",
        start_frame=0,
        frame_count=3,
        columns=8,
        rows=4,
        fps=20.0,
    )

    expected_duration = (
        1.0 / 20.0
    )

    for frame in clip.frames:
        assert frame.duration == pytest.approx(
            expected_duration
        )


def test_from_grid_preserves_loop_flag():
    clip = AnimationClip.from_grid(
        "attack",
        start_frame=0,
        frame_count=3,
        columns=4,
        rows=2,
        fps=10.0,
        loop=False,
    )

    assert clip.loop is False


def test_from_grid_first_cell_uv():
    clip = AnimationClip.from_grid(
        "frame",
        start_frame=0,
        frame_count=1,
        columns=4,
        rows=2,
        fps=10.0,
    )

    assert clip.frames[0].uv == pytest.approx(
        (
            0.0,
            0.0,
            0.25,
            0.5,
        )
    )


def test_from_grid_middle_cell_uv():
    clip = AnimationClip.from_grid(
        "frame",
        start_frame=5,
        frame_count=1,
        columns=4,
        rows=2,
        fps=10.0,
    )

    # Index 5:
    #
    # row    = 1
    # column = 1
    #
    # cell width  = 1 / 4 = 0.25
    # cell height = 1 / 2 = 0.5

    assert clip.frames[0].uv == pytest.approx(
        (
            0.25,
            0.5,
            0.25,
            0.5,
        )
    )


def test_from_grid_last_cell_uv():
    clip = AnimationClip.from_grid(
        "frame",
        start_frame=7,
        frame_count=1,
        columns=4,
        rows=2,
        fps=10.0,
    )

    assert clip.frames[0].uv == pytest.approx(
        (
            0.75,
            0.5,
            0.25,
            0.5,
        )
    )


def test_from_grid_can_cross_rows():
    clip = AnimationClip.from_grid(
        "effect",
        start_frame=2,
        frame_count=4,
        columns=4,
        rows=2,
        fps=10.0,
    )

    indices = [
        frame.index
        for frame in clip.frames
    ]

    assert indices == [
        2,
        3,
        4,
        5,
    ]

    assert clip.frames[0].uv == pytest.approx(
        (
            0.5,
            0.0,
            0.25,
            0.5,
        )
    )

    assert clip.frames[2].uv == pytest.approx(
        (
            0.0,
            0.5,
            0.25,
            0.5,
        )
    )


# ==============================================================
# AnimationClip.from_grid validation
# ==============================================================


def test_from_grid_rejects_zero_columns():
    with pytest.raises(
        ValueError
    ):
        AnimationClip.from_grid(
            "bad",
            start_frame=0,
            frame_count=1,
            columns=0,
            rows=2,
            fps=10.0,
        )


def test_from_grid_rejects_zero_rows():
    with pytest.raises(
        ValueError
    ):
        AnimationClip.from_grid(
            "bad",
            start_frame=0,
            frame_count=1,
            columns=4,
            rows=0,
            fps=10.0,
        )


def test_from_grid_rejects_negative_start_frame():
    with pytest.raises(
        ValueError
    ):
        AnimationClip.from_grid(
            "bad",
            start_frame=-1,
            frame_count=1,
            columns=4,
            rows=2,
            fps=10.0,
        )


def test_from_grid_rejects_zero_frame_count():
    with pytest.raises(
        ValueError
    ):
        AnimationClip.from_grid(
            "bad",
            start_frame=0,
            frame_count=0,
            columns=4,
            rows=2,
            fps=10.0,
        )


def test_from_grid_rejects_zero_fps():
    with pytest.raises(
        ValueError
    ):
        AnimationClip.from_grid(
            "bad",
            start_frame=0,
            frame_count=1,
            columns=4,
            rows=2,
            fps=0.0,
        )


def test_from_grid_rejects_start_frame_outside_grid():
    with pytest.raises(
        ValueError
    ):
        AnimationClip.from_grid(
            "bad",
            start_frame=8,
            frame_count=1,
            columns=4,
            rows=2,
            fps=10.0,
        )


def test_from_grid_rejects_range_outside_grid():
    with pytest.raises(
        ValueError
    ):
        AnimationClip.from_grid(
            "bad",
            start_frame=6,
            frame_count=3,
            columns=4,
            rows=2,
            fps=10.0,
        )


# ==============================================================
# AnimationClip.from_row
# ==============================================================


def test_from_row_creates_expected_indices():
    clip = AnimationClip.from_row(
        "walk_right",
        row=2,
        start_column=1,
        frame_count=4,
        columns=8,
        rows=4,
        fps=12.0,
    )

    # Row 2 starts at:
    #
    # 2 * 8 = 16
    #
    # start_column = 1
    #
    # first index = 17

    indices = [
        frame.index
        for frame in clip.frames
    ]

    assert indices == [
        17,
        18,
        19,
        20,
    ]


def test_from_row_default_start_column_is_zero():
    clip = AnimationClip.from_row(
        "walk",
        row=1,
        frame_count=3,
        columns=6,
        rows=4,
        fps=12.0,
    )

    indices = [
        frame.index
        for frame in clip.frames
    ]

    assert indices == [
        6,
        7,
        8,
    ]


def test_from_row_creates_correct_uvs():
    clip = AnimationClip.from_row(
        "walk",
        row=1,
        start_column=2,
        frame_count=1,
        columns=4,
        rows=4,
        fps=12.0,
    )

    # row 1 / column 2
    #
    # cell size = 0.25 x 0.25

    assert clip.frames[0].uv == pytest.approx(
        (
            0.5,
            0.25,
            0.25,
            0.25,
        )
    )


def test_from_row_supports_single_frame():
    clip = AnimationClip.from_row(
        "idle",
        row=0,
        frame_count=1,
        columns=8,
        rows=8,
        fps=4.0,
    )

    assert clip.frame_count == 1
    assert clip.frames[0].index == 0


def test_from_row_supports_entire_row():
    clip = AnimationClip.from_row(
        "walk",
        row=3,
        frame_count=8,
        columns=8,
        rows=6,
        fps=12.0,
    )

    assert clip.frame_count == 8

    assert clip.frames[0].index == 24
    assert clip.frames[-1].index == 31


# ==============================================================
# AnimationClip.from_row validation
# ==============================================================


def test_from_row_rejects_negative_row():
    with pytest.raises(
        ValueError
    ):
        AnimationClip.from_row(
            "bad",
            row=-1,
            frame_count=1,
            columns=4,
            rows=4,
            fps=10.0,
        )


def test_from_row_rejects_row_outside_grid():
    with pytest.raises(
        ValueError
    ):
        AnimationClip.from_row(
            "bad",
            row=4,
            frame_count=1,
            columns=4,
            rows=4,
            fps=10.0,
        )


def test_from_row_rejects_negative_start_column():
    with pytest.raises(
        ValueError
    ):
        AnimationClip.from_row(
            "bad",
            row=0,
            start_column=-1,
            frame_count=1,
            columns=4,
            rows=4,
            fps=10.0,
        )


def test_from_row_rejects_start_column_outside_grid():
    with pytest.raises(
        ValueError
    ):
        AnimationClip.from_row(
            "bad",
            row=0,
            start_column=4,
            frame_count=1,
            columns=4,
            rows=4,
            fps=10.0,
        )


def test_from_row_rejects_zero_frame_count():
    with pytest.raises(
        ValueError
    ):
        AnimationClip.from_row(
            "bad",
            row=0,
            frame_count=0,
            columns=4,
            rows=4,
            fps=10.0,
        )


def test_from_row_rejects_range_past_row():
    with pytest.raises(
        ValueError
    ):
        AnimationClip.from_row(
            "bad",
            row=1,
            start_column=3,
            frame_count=2,
            columns=4,
            rows=4,
            fps=10.0,
        )


def test_from_row_rejects_zero_fps():
    with pytest.raises(
        ValueError
    ):
        AnimationClip.from_row(
            "bad",
            row=0,
            frame_count=1,
            columns=4,
            rows=4,
            fps=0.0,
        )