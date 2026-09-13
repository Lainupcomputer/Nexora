from __future__ import annotations

import pytest

from nexora.scene import Scene, SceneManager


def test_scene_manager_load():
    manager = SceneManager()
    scene = Scene("MainMenu")

    manager.load(scene)

    assert manager.get("MainMenu") is scene
    assert manager.is_loaded("MainMenu")
    assert manager.active_scene is None


def test_scene_manager_activate():
    manager = SceneManager()
    scene = Scene("Game")

    manager.load(scene)

    result = manager.activate("Game")

    assert result is scene
    assert manager.active_scene is scene


def test_scene_manager_rejects_duplicate_scene():
    manager = SceneManager()

    manager.load(Scene("Game"))

    with pytest.raises(ValueError):
        manager.load(Scene("Game"))


def test_scene_manager_activate_unknown_scene():
    manager = SceneManager()

    with pytest.raises(KeyError):
        manager.activate("Game")


def test_scene_manager_unload():
    manager = SceneManager()
    scene = Scene("Game")
    node = scene.create_node("Player")

    manager.load(scene)

    assert scene.world.is_alive(node.entity)

    manager.unload("Game")

    assert not scene.world.is_alive(node.entity)
    assert not manager.is_loaded("Game")
    assert manager.active_scene is None


def test_scene_manager_unload_active_scene():
    manager = SceneManager()
    scene = Scene("Game")

    manager.load(scene)
    manager.activate("Game")

    manager.unload("Game")

    assert manager.active_scene is None
    assert manager.get("Game") is None


def test_scene_manager_clear():
    manager = SceneManager()

    scene_a = Scene("Menu")
    scene_b = Scene("Game")

    node_a = scene_a.create_node("MenuNode")
    node_b = scene_b.create_node("Player")

    manager.load(scene_a)
    manager.load(scene_b)
    manager.activate("Game")

    manager.clear()

    assert manager.active_scene is None
    assert not manager.is_loaded("Menu")
    assert not manager.is_loaded("Game")

    assert not scene_a.world.is_alive(node_a.entity)
    assert not scene_b.world.is_alive(node_b.entity)
    