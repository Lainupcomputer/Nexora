from __future__ import annotations

import pytest

from nexora.scene.scene import (
    Scene,
    SceneState,
)
from nexora.nodes import Node

class TrackingScene(Scene):
    def __init__(
        self,
        name: str,
    ) -> None:
        super().__init__(
            name
        )

        self.events: list[
            tuple
        ] = []

    def on_enter(
        self,
        previous_state: SceneState,
    ) -> None:
        self.events.append(
            (
                "enter",
                previous_state,
            )
        )

    def on_exit(
        self,
        previous_state: SceneState,
    ) -> None:
        self.events.append(
            (
                "exit",
                previous_state,
            )
        )

    def on_pause(
        self,
    ) -> None:
        self.events.append(
            (
                "pause",
            )
        )

    def on_resume(
        self,
    ) -> None:
        self.events.append(
            (
                "resume",
            )
        )


# ==============================================================
# CREATION
# ==============================================================


def test_scene_initial_state() -> None:
    scene = Scene(
        "Test"
    )

    assert (
        scene.name
        == "Test"
    )

    assert (
        scene.state
        == SceneState.CREATED
    )

    assert (
        scene.active
        is False
    )

    assert (
        scene.paused
        is False
    )

    assert (
        scene.destroyed
        is False
    )


def test_scene_rejects_empty_name() -> None:
    with pytest.raises(
        ValueError
    ):
        Scene(
            ""
        )


# ==============================================================
# ENTER
# ==============================================================


def test_scene_enter() -> None:
    scene = TrackingScene(
        "Test"
    )

    scene.enter()

    assert (
        scene.state
        == SceneState.ACTIVE
    )

    assert (
        scene.active
        is True
    )

    assert scene.events == [
        (
            "enter",
            SceneState.CREATED,
        )
    ]


def test_scene_enter_twice_is_noop() -> None:
    scene = TrackingScene(
        "Test"
    )

    scene.enter()
    scene.enter()

    assert len(
        scene.events
    ) == 1


# ==============================================================
# EXIT
# ==============================================================


def test_scene_exit() -> None:
    scene = TrackingScene(
        "Test"
    )

    scene.enter()
    scene.exit()

    assert (
        scene.state
        == SceneState.INACTIVE
    )

    assert scene.events == [
        (
            "enter",
            SceneState.CREATED,
        ),
        (
            "exit",
            SceneState.ACTIVE,
        ),
    ]


def test_scene_exit_inactive_is_noop() -> None:
    scene = TrackingScene(
        "Test"
    )

    scene.exit()

    assert (
        scene.state
        == SceneState.CREATED
    )

    assert (
        scene.events
        == []
    )


# ==============================================================
# PAUSE / RESUME
# ==============================================================


def test_scene_pause() -> None:
    scene = TrackingScene(
        "Test"
    )

    scene.enter()
    scene.pause()

    assert (
        scene.state
        == SceneState.PAUSED
    )

    assert (
        scene.paused
        is True
    )

    assert scene.events == [
        (
            "enter",
            SceneState.CREATED,
        ),
        (
            "pause",
        ),
    ]


def test_scene_pause_requires_active_scene() -> None:
    scene = Scene(
        "Test"
    )

    with pytest.raises(
        RuntimeError
    ):
        scene.pause()


def test_scene_resume() -> None:
    scene = TrackingScene(
        "Test"
    )

    scene.enter()
    scene.pause()
    scene.resume()

    assert (
        scene.state
        == SceneState.ACTIVE
    )

    assert scene.events == [
        (
            "enter",
            SceneState.CREATED,
        ),
        (
            "pause",
        ),
        (
            "resume",
        ),
    ]


def test_scene_resume_requires_paused_scene() -> None:
    scene = Scene(
        "Test"
    )

    with pytest.raises(
        RuntimeError
    ):
        scene.resume()


# ==============================================================
# DESTROY
# ==============================================================


def test_scene_destroy() -> None:
    scene = TrackingScene(
        "Test"
    )

    scene.enter()
    scene.destroy()

    assert (
        scene.state
        == SceneState.DESTROYED
    )

    assert (
        scene.destroyed
        is True
    )

    assert (
        scene.active
        is False
    )

    assert scene.events == [
        (
            "enter",
            SceneState.CREATED,
        ),
        (
            "exit",
            SceneState.ACTIVE,
        ),
    ]


def test_scene_destroy_twice_is_safe() -> None:
    scene = Scene(
        "Test"
    )

    scene.destroy()
    scene.destroy()

    assert (
        scene.destroyed
        is True
    )


def test_destroyed_scene_cannot_enter() -> None:
    scene = Scene(
        "Test"
    )

    scene.destroy()

    with pytest.raises(
        RuntimeError
    ):
        scene.enter()


# ==============================================================
# UPDATE STATE
# ==============================================================


def test_inactive_scene_does_not_update(
    monkeypatch,
) -> None:
    scene = Scene(
        "Test"
    )

    called = {
        "root": False,
        "world": False,
    }

    def root_update(
        delta_time,
    ):
        called["root"] = True

    def world_update(
        delta_time,
    ):
        called["world"] = True

    monkeypatch.setattr(
        scene.root,
        "update_tree",
        root_update,
    )

    monkeypatch.setattr(
        scene.world,
        "update",
        world_update,
    )

    scene.update(
        0.016
    )

    assert called == {
        "root": False,
        "world": False,
    }


def test_active_scene_updates(
    monkeypatch,
) -> None:
    scene = Scene(
        "Test"
    )

    called = {
        "root": False,
        "world": False,
    }

    def root_update(
        delta_time,
    ):
        called["root"] = True

    def world_update(
        delta_time,
    ):
        called["world"] = True

    monkeypatch.setattr(
        scene.root,
        "update_tree",
        root_update,
    )

    monkeypatch.setattr(
        scene.world,
        "update",
        world_update,
    )

    scene.enter()

    scene.update(
        0.016
    )

    assert called == {
        "root": True,
        "world": True,
    }

def test_scene_camera_defaults_to_none() -> None:
    scene = Scene(
        "Test"
    )

    assert (
        scene.camera
        is None
    )


def test_scene_can_assign_camera() -> None:
    scene = Scene(
        "Test"
    )

    camera = Node(
        "Camera",
        scene.world,
    )

    scene.camera = camera

    assert (
        scene.camera
        is camera
    )


def test_scene_rejects_camera_from_other_world() -> None:
    scene_a = Scene(
        "A"
    )

    scene_b = Scene(
        "B"
    )

    camera = Node(
        "Camera",
        scene_b.world,
    )

    with pytest.raises(
        ValueError
    ):
        scene_a.camera = camera


def test_scene_clear_camera() -> None:
    scene = Scene(
        "Test"
    )

    camera = Node(
        "Camera",
        scene.world,
    )

    scene.camera = camera

    scene.clear_camera()

    assert (
        scene.camera
        is None
    )


def test_scene_destroy_clears_camera() -> None:
    scene = Scene(
        "Test"
    )

    camera = Node(
        "Camera",
        scene.world,
    )

    scene.camera = camera

    scene.destroy()

    assert (
        scene.camera
        is None
    )