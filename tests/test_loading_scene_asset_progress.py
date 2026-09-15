from __future__ import annotations

import pytest

from nexora.scene.loading import SceneLoadTask


def test_stage_progress_is_exposed_in_progress_info() -> None:
    task = SceneLoadTask("Loading")
    stage_ref = {}

    def update(_dt: float) -> bool:
        stage = stage_ref["stage"]
        stage.progress = 0.5
        stage.status = "Initialisiere Assets: Audio 50%"
        return False

    stage = task.add_stage(
        "assets_audio",
        status="Initialisiere Assets: Audio 0%",
        update=update,
    )
    stage_ref["stage"] = stage

    task.update(0.016)
    info = task.progress_info

    assert info.stage_name == "assets_audio"
    assert info.stage_progress == pytest.approx(0.5)
    assert info.status == "Initialisiere Assets: Audio 50%"
    assert info.progress == pytest.approx(0.5)


def test_completed_stage_status_can_remain_visible_before_next_stage() -> None:
    task = SceneLoadTask("Assets")
    state = {"step": 0}

    def update(_dt: float) -> bool:
        stage = task.current_stage

        if state["step"] == 0:
            stage.progress = 1.0
            stage.status = "Initialisiere Assets: Font 100%"
            state["step"] = 1
            return False

        return True

    task.add_stage(
        "assets_font",
        status="Initialisiere Assets: Font 0%",
        update=update,
    )
    task.add_stage(
        "assets_audio",
        status="Initialisiere Assets: Audio 0%",
        callback=lambda: None,
    )

    task.update(0.016)
    assert task.status == "Initialisiere Assets: Font 100%"
    assert task.current_stage.name == "assets_font"

    task.update(0.016)
    assert task.current_stage.name == "assets_audio"
    assert task.status == "Initialisiere Assets: Audio 0%"
