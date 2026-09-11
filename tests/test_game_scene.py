from nexora.core.game import Game
from nexora.scene import Scene
from nexora.scene import Scene, SceneManager


def test_game_scene_assignment():
    game = Game()

    scene = Scene("MainScene")

    game.scene = scene

    assert game.scene is scene
    assert game.scene.name == "MainScene"


def test_game_scene_replacement():
    game = Game()

    first_scene = Scene("First")
    second_scene = Scene("Second")

    node = first_scene.create_node("Player")

    game.scene = first_scene

    first_entity = node.entity

    assert first_scene.world.is_alive(first_entity)

    game.scene = second_scene

    assert game.scene is second_scene
    assert not first_scene.world.is_alive(first_entity)


def test_game_scene_shutdown():
    game = Game()

    scene = Scene("MainScene")
    node = scene.create_node("Player")

    game.scene = scene

    entity = node.entity

    assert scene.world.is_alive(entity)

    game.shutdown()

    assert game.scene is None
    assert not scene.world.is_alive(entity)

def test_game_scene_replacement_destroys_old_scene():
    game = Game(
        title="Scene Test",
        width=320,
        height=240,
        target_fps=60,
    )

    old_scene = Scene("OldScene")
    old_node = old_scene.create_node("OldNode")

    assert old_scene.world.entity_count() == 2
    assert old_scene.world.is_alive(old_node.entity)

    game.scene = old_scene

    new_scene = Scene("NewScene")
    new_node = new_scene.create_node("NewNode")

    game.scene = new_scene

    assert game.scene is new_scene

    assert not old_scene.world.is_alive(old_node.entity)
    assert old_scene.world.entity_count() == 0

    assert new_scene.world.is_alive(new_node.entity)
    assert new_scene.world.entity_count() == 2

def test_game_has_scene_manager():
    game = Game(
        title="Scene Test",
        width=320,
        height=240,
        target_fps=60,
    )

    assert isinstance(game.scenes, SceneManager)


def test_game_scene_manager_load_and_activate():
    game = Game(
        title="Scene Test",
        width=320,
        height=240,
        target_fps=60,
    )

    scene = Scene("Game")

    game.scenes.load(scene)

    assert game.scenes.get("Game") is scene
    assert game.scenes.active_scene is None

    result = game.scenes.activate("Game")

    assert result is scene
    assert game.scenes.active_scene is scene


def test_game_scene_manager_uses_active_scene():
    game = Game(
        title="Scene Test",
        width=320,
        height=240,
        target_fps=60,
    )

    scene = Scene("Game")
    node = scene.create_node("Player")

    game.scenes.load(scene)
    game.scenes.activate("Game")

    assert game.scenes.active_scene is scene
    assert game.scene is scene
    assert scene.world.is_alive(node.entity)

def test_game_scene_setter_syncs_scene_manager():
    game = Game(
        title="Scene Test",
        width=320,
        height=240,
        target_fps=60,
    )

    scene = Scene("Game")

    game.scenes.load(scene)
    game.scene = scene

    assert game.scene is scene
    assert game.scenes.active_scene is scene


