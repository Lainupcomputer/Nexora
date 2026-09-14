from __future__ import annotations

import pytest

from nexora.scene.loading import (
    LoadingState,
    SceneLoadTask,
)


def test_load_task_starts_pending() -> None:
    task = SceneLoadTask(
        "Dungeon"
    )

    assert (
        task.state
        == LoadingState.PENDING
    )

    assert (
        task.progress
        == 0.0
    )


def test_empty_task_completes_immediately() -> None:
    task = SceneLoadTask(
        "Empty"
    )

    task.start()

    assert (
        task.done
        is True
    )

    assert (
        task.progress
        == 1.0
    )


def test_callback_stage_completes() -> None:
    task = SceneLoadTask(
        "Dungeon"
    )

    called = []

    task.add_stage(
        "layout",
        callback=lambda: (
            called.append(
                "layout"
            )
        ),
    )

    task.update(
        0.016
    )

    assert called == [
        "layout"
    ]

    assert (
        task.done
        is True
    )

    assert (
        task.progress
        == 1.0
    )


def test_multiple_stages_progress() -> None:
    task = SceneLoadTask(
        "Dungeon"
    )

    task.add_stage(
        "layout",
        callback=lambda: None,
    )

    task.add_stage(
        "rooms",
        callback=lambda: None,
    )

    task.update(
        0.016
    )

    assert (
        task.progress
        == pytest.approx(
            0.5
        )
    )

    assert (
        task.done
        is False
    )

    task.update(
        0.016
    )

    assert (
        task.progress
        == 1.0
    )

    assert (
        task.done
        is True
    )


def test_weighted_progress() -> None:
    task = SceneLoadTask(
        "Dungeon"
    )

    task.add_stage(
        "layout",
        weight=1.0,
        callback=lambda: None,
    )

    task.add_stage(
        "world",
        weight=3.0,
        callback=lambda: None,
    )

    task.update(
        0.016
    )

    assert (
        task.progress
        == pytest.approx(
            0.25
        )
    )


def test_incremental_stage() -> None:
    task = SceneLoadTask(
        "Dungeon"
    )

    frames = {
        "count": 0,
    }

    def update_stage(
        delta_time: float,
    ) -> bool:
        frames["count"] += 1

        return (
            frames["count"]
            >= 3
        )

    task.add_stage(
        "generation",
        update=update_stage,
    )

    task.update(
        0.016
    )

    assert (
        task.done
        is False
    )

    task.update(
        0.016
    )

    assert (
        task.done
        is False
    )

    task.update(
        0.016
    )

    assert (
        task.done
        is True
    )


def test_stage_failure_marks_task_failed() -> None:
    task = SceneLoadTask(
        "Dungeon"
    )

    def broken() -> None:
        raise RuntimeError(
            "generation failed"
        )

    task.add_stage(
        "generation",
        callback=broken,
    )

    task.update(
        0.016
    )

    assert (
        task.failed
        is True
    )

    assert isinstance(
        task.error,
        RuntimeError,
    )


def test_cancel_task() -> None:
    task = SceneLoadTask(
        "Dungeon"
    )

    task.add_stage(
        "generation",
        callback=lambda: None,
    )

    task.cancel()

    assert (
        task.cancelled
        is True
    )

    task.update(
        0.016
    )

    assert (
        task.cancelled
        is True
    )


def test_progress_info() -> None:
    task = SceneLoadTask(
        "Dungeon"
    )

    task.add_stage(
        "layout",
        status="Generating layout...",
        callback=lambda: None,
    )

    task.add_stage(
        "rooms",
        status="Building rooms...",
        callback=lambda: None,
    )

    task.update(
        0.016
    )

    info = (
        task.progress_info
    )

    assert (
        info.progress
        == pytest.approx(
            0.5
        )
    )

    assert (
        info.status
        == "Building rooms..."
    )

    assert (
        info.stage_name
        == "rooms"
    )

    assert (
        info.stage_index
        == 1
    )

    assert (
        info.stage_count
        == 2
    )