from __future__ import annotations

import pytest

from nexora.animation import AnimationClip, AnimationFrame
from nexora.ecs.world import World
from nexora.nodes.entity import AttackProfile, CharacterController2D
from nexora.nodes.texture import AnimatedSprite
from nexora.scene.serialization.registry import NodeFactoryRegistry


class FakeInput:
    def __init__(self) -> None:
        self.down: set[str] = set()
        self.pressed: set[str] = set()
        self.mouse_position = (300.0, 200.0)

    def action_down(self, action: str) -> bool:
        return action in self.down

    def action_pressed(self, action: str) -> bool:
        return action in self.pressed


class FakeCamera:
    def screen_to_world(self, x: float, y: float, width: int, height: int) -> tuple[float, float]:
        return x - width / 2.0, y - height / 2.0


def make_controller() -> tuple[CharacterController2D, FakeInput]:
    world = World()
    controller = CharacterController2D("Player", world)
    input_manager = FakeInput()
    controller.set_input(input_manager)
    return controller, input_manager


def test_controller_uses_friction_and_eight_direction_facing() -> None:
    controller, input_manager = make_controller()

    input_manager.down.update({"move_right", "move_down"})
    controller.update(1.0 / 60.0)
    assert controller.current_state == "walk"
    assert controller.facing_direction == "south_east"
    assert controller.velocity.x == pytest.approx(controller.velocity.y)

    input_manager.down.clear()
    controller.update(0.2)
    assert controller.current_state == "idle"
    assert controller.velocity.tuple == pytest.approx((0.0, 0.0))


@pytest.mark.parametrize(
    ("vector", "direction"),
    [
        ((0.0, -1.0), "north"), ((1.0, -1.0), "north_east"),
        ((1.0, 0.0), "east"), ((1.0, 1.0), "south_east"),
        ((0.0, 1.0), "south"), ((-1.0, 1.0), "south_west"),
        ((-1.0, 0.0), "west"), ((-1.0, -1.0), "north_west"),
    ],
)
def test_direction_mapping_covers_all_eight_directions(vector, direction) -> None:
    assert CharacterController2D._direction_from_vector(*vector) == direction


def test_run_and_roll_are_state_machine_states() -> None:
    controller, input_manager = make_controller()
    input_manager.down.update({"move_up", "run"})
    controller.update(1.0 / 60.0)
    assert controller.current_state == "run"
    assert controller.velocity.y < 0.0

    input_manager.pressed.add("roll")
    controller.update(1.0 / 60.0)
    assert controller.current_state == "roll"
    assert controller.invulnerable is True


def test_attack_profile_targets_mouse_and_selects_animation() -> None:
    world = World()
    controller = CharacterController2D("Player", world)
    input_manager = FakeInput()
    controller.set_input(input_manager)
    controller.set_camera(FakeCamera(), viewport_size=(800, 600))

    sprite = AnimatedSprite("Sprite", world)
    sprite.add_animation(AnimationClip("attack_sword_east", (AnimationFrame(0, 0.2),)))
    controller.add_child(sprite)
    controller.set_animation_driver(sprite)
    controller.register_weapon(
        "sword",
        AttackProfile("sword", animation="attack_{weapon}_{direction}", duration=0.2),
    )
    controller.set_weapon("sword")
    input_manager.pressed.add("attack")
    input_manager.mouse_position = (800.0, 300.0)

    controller.update(1.0 / 60.0)
    assert controller.current_state == "attack"
    assert controller.attack_target_world == pytest.approx((400.0, 0.0))
    assert controller.facing_direction == "east"
    assert sprite.current_animation_name == "attack_sword_east"


def test_damage_selects_hit_and_injury_states() -> None:
    controller, _ = make_controller()
    controller.update(1.0 / 60.0)

    assert controller.take_damage(10.0, critical=True)
    controller.update(0.01)
    assert controller.current_state == "get_critical_hit"

    controller.update(1.0)
    assert controller.take_damage(70.0)
    controller.update(0.01)
    assert controller.current_state == "heavily_injured"


def test_controller_is_registered_and_serializable() -> None:
    registry = NodeFactoryRegistry()
    world = World()
    controller = CharacterController2D("Player", world)
    controller.walk_speed = 145.0
    controller.floor_type = "grass"
    controller.register_weapon("sword", {"animation": "attack_sword_{direction}", "damage": 12})

    assert registry.type_id_for(controller) == "CharacterController2D"
    state = registry.dump_properties(controller)
    loaded = registry.create("CharacterController2D", "Loaded", world)
    registry.load_properties(loaded, state)
    assert loaded.walk_speed == pytest.approx(145.0)
    assert loaded.floor_type == "grass"
    assert loaded.weapon_profiles["sword"].damage == pytest.approx(12.0)
