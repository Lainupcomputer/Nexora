import pytest
from nexora.ecs.system import System

from nexora.scene import Node, Scene
from nexora.nodes.ui.controls.button import Button
from nexora.input.input import InputManager



def test_scene_creation():
    scene = Scene("TestScene")

    assert scene.name == "TestScene"
    assert scene.root.name == "Root"


def test_scene_node_creation():
    scene = Scene("TestScene")

    player = scene.create_node("Player")
    weapon = scene.create_node("Weapon", player)
    camera = scene.create_node("Camera")

    assert player.parent is scene.root
    assert weapon.parent is player
    assert camera.parent is scene.root


def test_scene_lookup():
    scene = Scene("TestScene")

    player = scene.create_node("Player")
    weapon = scene.create_node("Weapon", player)
    camera = scene.create_node("Camera")

    assert scene.find("Player") is player
    assert scene.find("Weapon") is weapon
    assert scene.find("Camera") is camera


def test_scene_ecs_integration():
    scene = Scene("TestScene")

    player = scene.create_node("Player")
    weapon = scene.create_node("Weapon", player)
    camera = scene.create_node("Camera")

    assert scene.world.is_alive(player.entity)
    assert scene.world.is_alive(weapon.entity)
    assert scene.world.is_alive(camera.entity)


def test_scene_destroy():
    scene = Scene("TestScene")

    player = scene.create_node("Player")
    weapon = scene.create_node("Weapon", player)
    camera = scene.create_node("Camera")

    scene.destroy()

    assert not scene.world.is_alive(player.entity)
    assert not scene.world.is_alive(weapon.entity)
    assert not scene.world.is_alive(camera.entity)


def test_scene_nodes():
    scene = Scene("TestScene")

    player = scene.create_node("Player")
    camera = scene.create_node("Camera")

    assert scene.nodes == (player, camera)


def test_scene_add_node():
    scene = Scene("TestScene")

    player = scene.create_node("Player")
    weapon = Node("Weapon", scene.world)

    scene.add_node(weapon, player)

    assert weapon.parent is player
    assert scene.find("Weapon") is weapon


def test_scene_remove_node():
    scene = Scene("TestScene")

    player = scene.create_node("Player")
    weapon = scene.create_node("Weapon", player)

    scene.remove_node(player)

    assert player.parent is None
    assert scene.nodes == ()
    assert scene.find("Player") is None

    assert scene.world.is_alive(player.entity)
    assert scene.world.is_alive(weapon.entity)


def test_scene_rejects_foreign_node():
    scene = Scene("TestScene")
    other_scene = Scene("OtherScene")

    foreign_node = Node("Foreign", other_scene.world)

    with pytest.raises(ValueError):
        scene.add_node(foreign_node)


def test_scene_rejects_foreign_parent():
    scene = Scene("TestScene")
    other_scene = Scene("OtherScene")

    foreign_parent = Node("ForeignParent", other_scene.world)
    node = scene.create_node("Node")

    with pytest.raises(ValueError):
        scene.add_node(node, foreign_parent)

def test_scene_update():
    scene = Scene("TestScene")

    class TestSystem(System):
        def __init__(self):
            self.update_count = 0
            self.last_delta = None

        def update(self, world, delta_time):
            self.update_count += 1
            self.last_delta = delta_time

    system = TestSystem()
    scene.world.add_system(system)

    scene.update(0.016)

    assert system.update_count == 1
    assert system.last_delta == 0.016

def test_scene_fixed_update():
    scene = Scene("TestScene")

    class TestSystem(System):
        def __init__(self):
            self.update_count = 0
            self.last_delta = None

        def fixed_update(self, world, fixed_delta_time):
            self.update_count += 1
            self.last_delta = fixed_delta_time

    system = TestSystem()
    scene.world.add_system(system)

    scene.fixed_update(0.02)

    assert system.update_count == 1
    assert system.last_delta == 0.02

def test_scene_updates_ui_input() -> None:
    scene = Scene("UITest")

    button = Button(
        "Button",
        scene.world,
    )

    button.size = (
        200.0,
        100.0,
    )

    scene.ui.add_child(
        button,
    )

    input_manager = InputManager()

    input_manager.initialize()

    scene.ui_input.set_mouse_position(
        50.0,
        20.0,
    )

    # Mouse position is normally supplied by InputManager.
    input_manager._mouse_x = 50.0
    input_manager._mouse_y = 20.0

    scene.update_input(
        input_manager,
    )

    assert scene.ui_input.mouse_position == (
        50.0,
        20.0,
    )

    assert button.hovered is True

def test_scene_updates_ui_from_input_manager() -> None:
    scene = Scene("UITest")

    button = Button(
        "Button",
        scene.world,
    )

    button.size = (
        200.0,
        100.0,
    )

    scene.ui.add_child(
        button,
    )

    class FakeInputManager:
        mouse_position = (
            50.0,
            20.0,
        )

        def mouse_down(
            self,
            button: str,
        ) -> bool:
            return True

        def mouse_pressed(
            self,
            button: str,
        ) -> bool:
            return True

        def mouse_released(
            self,
            button: str,
        ) -> bool:
            return False

    input_manager = FakeInputManager()

    scene.update_input(
        input_manager,
    )

    assert scene.ui_input.mouse_position == (
        50.0,
        20.0,
    )

    assert scene.ui_input.mouse_left_down is True
    assert scene.ui_input.mouse_left_pressed is True
    assert scene.ui_input.mouse_left_released is False

    assert button.hovered is True
    assert button.pressed is True
    