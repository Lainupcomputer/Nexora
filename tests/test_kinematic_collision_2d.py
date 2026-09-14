from __future__ import annotations

import pytest

from nexora.ecs.world import World
from nexora.nodes import (
    CharacterBody2D,
    CollisionShape2D,
    Node,
    StaticBody2D,
)


def create_character(
    world: World,
) -> CharacterBody2D:
    body = CharacterBody2D(
        "Player",
        world,
    )

    shape = CollisionShape2D(
        "PlayerCollision",
        world,
        16.0,
        16.0,
    )

    body.add_child(
        shape
    )

    return body


def create_wall(
    world: World,
    x: float,
    y: float,
) -> StaticBody2D:
    wall = StaticBody2D(
        "Wall",
        world,
    )

    wall.transform.x = x
    wall.transform.y = y

    shape = CollisionShape2D(
        "WallCollision",
        world,
        32.0,
        32.0,
    )

    wall.add_child(
        shape
    )

    return wall


def test_right_collision_contains_body():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    wall = create_wall(
        world,
        32.0,
        0.0,
    )

    root.add_child(
        player
    )

    root.add_child(
        wall
    )

    player.velocity.x = 100.0

    result = player.move_and_slide(
        1.0
    )

    assert result.collision_count == 1

    collision = result.collisions[0]

    assert collision.collider is wall

    assert collision.normal == (
        -1.0,
        0.0,
    )


def test_right_contact_point():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    wall = create_wall(
        world,
        32.0,
        0.0,
    )

    root.add_child(
        player
    )

    root.add_child(
        wall
    )

    player.velocity.x = 100.0

    result = player.move_and_slide(
        1.0
    )

    collision = result.collisions[0]

    assert collision.point == pytest.approx(
        (
            32.0,
            8.0,
        )
    )


def test_right_collision_travel():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    wall = create_wall(
        world,
        32.0,
        0.0,
    )

    root.add_child(
        player
    )

    root.add_child(
        wall
    )

    player.velocity.x = 100.0

    result = player.move_and_slide(
        1.0
    )

    collision = result.collisions[0]

    assert collision.travel_x == pytest.approx(
        16.0
    )

    assert collision.remainder_x == pytest.approx(
        84.0
    )


def test_floor_collision_normal():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    floor = create_wall(
        world,
        0.0,
        32.0,
    )

    root.add_child(
        player
    )

    root.add_child(
        floor
    )

    player.velocity.y = 100.0

    result = player.move_and_slide(
        1.0
    )

    collision = result.collisions[0]

    assert collision.normal == (
        0.0,
        -1.0,
    )

    assert player.is_on_floor


def test_ceiling_collision_normal():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    ceiling = create_wall(
        world,
        0.0,
        32.0,
    )

    player.transform.y = 80.0

    root.add_child(
        player
    )

    root.add_child(
        ceiling
    )

    player.velocity.y = -100.0

    result = player.move_and_slide(
        1.0
    )

    collision = result.collisions[0]

    assert collision.normal == (
        0.0,
        1.0,
    )

    assert player.is_on_ceiling


def test_get_last_slide_collision():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    wall = create_wall(
        world,
        32.0,
        0.0,
    )

    root.add_child(
        player
    )

    root.add_child(
        wall
    )

    player.velocity.x = 100.0

    player.move_and_slide(
        1.0
    )

    collision = (
        player.get_last_slide_collision()
    )

    assert collision is not None
    assert collision.collider is wall


def test_no_collision_returns_none():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    root.add_child(
        player
    )

    player.velocity.x = 10.0

    result = player.move_and_slide(
        1.0
    )

    assert not result.collided
    assert result.collision_count == 0

    assert (
        player.get_last_slide_collision()
        is None
    )


def test_slide_collision_count():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    wall = create_wall(
        world,
        32.0,
        0.0,
    )

    root.add_child(
        player
    )

    root.add_child(
        wall
    )

    player.velocity.x = 100.0

    player.move_and_slide(
        1.0
    )

    assert (
        player.slide_collision_count
        == 1
    )


def test_collision_shape_references():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    wall = create_wall(
        world,
        32.0,
        0.0,
    )

    root.add_child(
        player
    )

    root.add_child(
        wall
    )

    player.velocity.x = 100.0

    player.move_and_slide(
        1.0
    )

    collision = (
        player.get_last_slide_collision()
    )

    assert collision is not None

    assert (
        collision.local_shape
        is player.primary_collision_shape
    )

    assert (
        collision.collider_shape
        is wall.primary_collision_shape
    )