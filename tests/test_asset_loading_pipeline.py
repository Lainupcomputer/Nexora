from __future__ import annotations

from nexora.scene.loading import LoadingStage, SceneLoadTask


def test_loading_stage_partial_progress_affects_task_progress():
    task = SceneLoadTask("Demo")
    holder = {}

    def update(_dt: float) -> bool:
        holder["stage"].progress = 0.5
        return False

    stage = task.add_stage("assets", weight=2.0, update=update)
    holder["stage"] = stage

    task.update(0.016)

    assert stage.progress == 0.5
    assert task.progress == 0.5


def test_finished_stage_forces_progress_to_one():
    task = SceneLoadTask("Demo")
    stage = task.add_stage("assets", update=lambda _dt: True)

    task.update(0.016)

    assert stage.finished
    assert stage.progress == 1.0
    assert task.progress == 1.0


def test_weighted_progress_includes_active_stage_fraction():
    task = SceneLoadTask("Demo")
    task.add_stage("first", weight=1.0, callback=lambda: None)
    holder = {}

    def update(_dt: float) -> bool:
        holder["stage"].progress = 0.5
        return False

    stage = task.add_stage("second", weight=3.0, update=update)
    holder["stage"] = stage

    task.update(0.016)  # first stage finishes
    assert task.progress == 0.25

    task.update(0.016)  # second stage reaches 50%
    assert task.progress == 0.625
