from __future__ import annotations

import pytest

from nexora.scene.manager import (
    SceneManager,
)

from nexora.scene.scene import (
    Scene,
    SceneState,
)


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

# ==============================================================
# REGISTRATION
# ==============================================================


def test_register_scene_does_not_load_it() -> None:
    manager = SceneManager()

    created = []

    def factory() -> Scene:
        scene = Scene(
            "Game"
        )

        created.append(
            scene
        )

        return scene

    manager.register(
        "Game",
        factory,
    )

    assert (
        manager.is_registered(
            "Game"
        )
        is True
    )

    assert (
        manager.is_loaded(
            "Game"
        )
        is False
    )

    assert (
        manager.get(
            "Game"
        )
        is None
    )

    assert (
        created
        == []
    )


def test_register_duplicate_scene_fails() -> None:
    manager = SceneManager()

    manager.register(
        "Game",
        lambda: Scene(
            "Game"
        ),
    )

    with pytest.raises(
        ValueError
    ):
        manager.register(
            "Game",
            lambda: Scene(
                "Game"
            ),
        )


def test_register_requires_callable_factory() -> None:
    manager = SceneManager()

    with pytest.raises(
        TypeError
    ):
        manager.register(
            "Game",
            None,
        )


def test_unregister_scene() -> None:
    manager = SceneManager()

    manager.register(
        "Game",
        lambda: Scene(
            "Game"
        ),
    )

    manager.unregister(
        "Game"
    )

    assert (
        manager.is_registered(
            "Game"
        )
        is False
    )


def test_unregister_unknown_scene_fails() -> None:
    manager = SceneManager()

    with pytest.raises(
        KeyError
    ):
        manager.unregister(
            "Missing"
        )


# ==============================================================
# LAZY LOADING
# ==============================================================


def test_change_scene_lazy_loads_registered_scene() -> None:
    manager = SceneManager()

    created = []

    def factory() -> Scene:
        scene = Scene(
            "Game"
        )

        created.append(
            scene
        )

        return scene

    manager.register(
        "Game",
        factory,
    )

    assert (
        created
        == []
    )

    scene = manager.change_scene(
        "Game"
    )

    assert len(
        created
    ) == 1

    assert (
        scene
        is created[0]
    )

    assert (
        manager.active_scene
        is scene
    )

    assert (
        scene.state
        == SceneState.ACTIVE
    )

    assert (
        manager.is_loaded(
            "Game"
        )
        is True
    )


def test_lazy_load_returns_existing_instance() -> None:
    manager = SceneManager()

    created = []

    def factory() -> Scene:
        scene = Scene(
            "Game"
        )

        created.append(
            scene
        )

        return scene

    manager.register(
        "Game",
        factory,
    )

    first = manager.load_registered(
        "Game"
    )

    second = manager.load_registered(
        "Game"
    )

    assert (
        first
        is second
    )

    assert len(
        created
    ) == 1


def test_ensure_loaded_constructs_registered_scene() -> None:
    manager = SceneManager()

    manager.register(
        "Game",
        lambda: Scene(
            "Game"
        ),
    )

    scene = manager.ensure_loaded(
        "Game"
    )

    assert isinstance(
        scene,
        Scene,
    )

    assert (
        scene.name
        == "Game"
    )

    assert (
        manager.is_loaded(
            "Game"
        )
        is True
    )


def test_unknown_scene_cannot_be_lazy_loaded() -> None:
    manager = SceneManager()

    with pytest.raises(
        KeyError
    ):
        manager.ensure_loaded(
            "Missing"
        )


# ==============================================================
# FACTORY VALIDATION
# ==============================================================


def test_factory_must_return_scene() -> None:
    manager = SceneManager()

    manager.register(
        "Broken",
        lambda: object(),
    )

    with pytest.raises(
        TypeError
    ):
        manager.load_registered(
            "Broken"
        )


def test_factory_scene_name_must_match_registration() -> None:
    manager = SceneManager()

    manager.register(
        "Game",
        lambda: Scene(
            "WrongName"
        ),
    )

    with pytest.raises(
        ValueError
    ):
        manager.load_registered(
            "Game"
        )


def test_factory_cannot_return_destroyed_scene() -> None:
    manager = SceneManager()

    def factory() -> Scene:
        scene = Scene(
            "Game"
        )

        scene.destroy()

        return scene

    manager.register(
        "Game",
        factory,
    )

    with pytest.raises(
        ValueError
    ):
        manager.load_registered(
            "Game"
        )


# ==============================================================
# KEEP LOADED
# ==============================================================


def test_keep_loaded_true_preserves_previous_scene() -> None:
    manager = SceneManager()

    manager.register(
        "Menu",
        lambda: Scene(
            "Menu"
        ),
        keep_loaded=True,
    )

    manager.register(
        "Game",
        lambda: Scene(
            "Game"
        ),
        keep_loaded=True,
    )

    menu = manager.change_scene(
        "Menu"
    )

    game = manager.change_scene(
        "Game"
    )

    assert (
        menu.destroyed
        is False
    )

    assert (
        menu.state
        == SceneState.INACTIVE
    )

    assert (
        manager.get(
            "Menu"
        )
        is menu
    )

    assert (
        manager.active_scene
        is game
    )


def test_keep_loaded_false_unloads_previous_scene() -> None:
    manager = SceneManager()

    manager.register(
        "Dungeon",
        lambda: Scene(
            "Dungeon"
        ),
        keep_loaded=False,
    )

    manager.register(
        "HQ",
        lambda: Scene(
            "HQ"
        ),
        keep_loaded=True,
    )

    dungeon = manager.change_scene(
        "Dungeon"
    )

    manager.change_scene(
        "HQ"
    )

    assert (
        dungeon.destroyed
        is True
    )

    assert (
        manager.get(
            "Dungeon"
        )
        is None
    )

    assert (
        manager.is_registered(
            "Dungeon"
        )
        is True
    )


# ==============================================================
# RECREATION
# ==============================================================


def test_transient_scene_is_recreated_after_unload() -> None:
    manager = SceneManager()

    created = []

    def dungeon_factory() -> Scene:
        scene = Scene(
            "Dungeon"
        )

        created.append(
            scene
        )

        return scene

    manager.register(
        "Dungeon",
        dungeon_factory,
        keep_loaded=False,
    )

    manager.register(
        "HQ",
        lambda: Scene(
            "HQ"
        ),
        keep_loaded=True,
    )

    first = manager.change_scene(
        "Dungeon"
    )

    manager.change_scene(
        "HQ"
    )

    second = manager.change_scene(
        "Dungeon"
    )

    assert len(
        created
    ) == 2

    assert (
        first
        is not second
    )

    assert (
        first.destroyed
        is True
    )

    assert (
        second.destroyed
        is False
    )

    assert (
        manager.active_scene
        is second
    )


# ==============================================================
# MANUALLY LOADED SCENES
# ==============================================================


def test_manual_scene_is_persistent_by_default() -> None:
    manager = SceneManager()

    manual = Scene(
        "Manual"
    )

    other = Scene(
        "Other"
    )

    manager.load(
        manual
    )

    manager.load(
        other
    )

    manager.change_scene(
        "Manual"
    )

    manager.change_scene(
        "Other"
    )

    assert (
        manual.destroyed
        is False
    )

    assert (
        manager.get(
            "Manual"
        )
        is manual
    )


# ==============================================================
# UNLOAD OVERRIDE
# ==============================================================


def test_unload_previous_true_overrides_keep_loaded() -> None:
    manager = SceneManager()

    manager.register(
        "Menu",
        lambda: Scene(
            "Menu"
        ),
        keep_loaded=True,
    )

    manager.register(
        "Game",
        lambda: Scene(
            "Game"
        ),
        keep_loaded=True,
    )

    menu = manager.change_scene(
        "Menu"
    )

    manager.change_scene(
        "Game",
        unload_previous=True,
    )

    assert (
        menu.destroyed
        is True
    )

    assert (
        manager.get(
            "Menu"
        )
        is None
    )


def test_unload_previous_false_overrides_transient_policy() -> None:
    manager = SceneManager()

    manager.register(
        "Dungeon",
        lambda: Scene(
            "Dungeon"
        ),
        keep_loaded=False,
    )

    manager.register(
        "HQ",
        lambda: Scene(
            "HQ"
        ),
        keep_loaded=True,
    )

    dungeon = manager.change_scene(
        "Dungeon"
    )

    manager.change_scene(
        "HQ",
        unload_previous=False,
    )

    assert (
        dungeon.destroyed
        is False
    )

    assert (
        manager.get(
            "Dungeon"
        )
        is dungeon
    )


# ==============================================================
# RELOAD
# ==============================================================


def test_reload_recreates_registered_scene() -> None:
    manager = SceneManager()

    created = []

    def factory() -> Scene:
        scene = Scene(
            "Game"
        )

        created.append(
            scene
        )

        return scene

    manager.register(
        "Game",
        factory,
    )

    first = manager.load_registered(
        "Game"
    )

    second = manager.reload(
        "Game"
    )

    assert len(
        created
    ) == 2

    assert (
        first
        is not second
    )

    assert (
        first.destroyed
        is True
    )

    assert (
        second.destroyed
        is False
    )

    assert (
        manager.get(
            "Game"
        )
        is second
    )


def test_reload_active_scene_keeps_it_active() -> None:
    manager = SceneManager()

    created = []

    def factory() -> Scene:
        scene = Scene(
            "Game"
        )

        created.append(
            scene
        )

        return scene

    manager.register(
        "Game",
        factory,
    )

    first = manager.change_scene(
        "Game"
    )

    second = manager.reload(
        "Game"
    )

    assert (
        first.destroyed
        is True
    )

    assert (
        manager.active_scene
        is second
    )

    assert (
        second.state
        == SceneState.ACTIVE
    )


def test_reload_requires_registration() -> None:
    manager = SceneManager()

    manager.load(
        Scene(
            "Game"
        )
    )

    with pytest.raises(
        KeyError
    ):
        manager.reload(
            "Game"
        )


# ==============================================================
# CLEAR
# ==============================================================


def test_clear_keeps_registrations_by_default() -> None:
    manager = SceneManager()

    manager.register(
        "Game",
        lambda: Scene(
            "Game"
        ),
    )

    scene = manager.change_scene(
        "Game"
    )

    manager.clear()

    assert (
        scene.destroyed
        is True
    )

    assert (
        manager.is_loaded(
            "Game"
        )
        is False
    )

    assert (
        manager.is_registered(
            "Game"
        )
        is True
    )


def test_clear_can_remove_registrations() -> None:
    manager = SceneManager()

    manager.register(
        "Game",
        lambda: Scene(
            "Game"
        ),
    )

    manager.change_scene(
        "Game"
    )

    manager.clear(
        clear_registrations=True,
    )

    assert (
        manager.is_loaded(
            "Game"
        )
        is False
    )

    assert (
        manager.is_registered(
            "Game"
        )
        is False
    )


# ==============================================================
# REGISTERED STACK SCENES
# ==============================================================


def test_push_scene_lazy_loads_registered_scene() -> None:
    manager = SceneManager()

    manager.register(
        "Game",
        lambda: Scene(
            "Game"
        ),
    )

    manager.register(
        "Pause",
        lambda: Scene(
            "Pause"
        ),
    )

    game = manager.change_scene(
        "Game"
    )

    assert (
        manager.is_loaded(
            "Pause"
        )
        is False
    )

    pause = manager.push_scene(
        "Pause"
    )

    assert (
        manager.is_loaded(
            "Pause"
        )
        is True
    )

    assert (
        game.state
        == SceneState.PAUSED
    )

    assert (
        pause.state
        == SceneState.ACTIVE
    )

    assert (
        manager.active_scene
        is pause
    )
    