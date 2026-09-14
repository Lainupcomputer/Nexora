from __future__ import annotations

import pytest

from nexora.ecs.world import World

from nexora.nodes import (
    Area2D,
    CharacterBody2D,
    CollisionShape2D,
    Node,
    StaticBody2D,
)


def create_character(
    world: World,
    name: str = "Player",
) -> CharacterBody2D:
    body = CharacterBody2D(
        name,
        world,
    )

    shape = CollisionShape2D(
        "Collision",
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
    name: str = "Wall",
) -> StaticBody2D:
    body = StaticBody2D(
        name,
        world,
    )

    shape = CollisionShape2D(
        "Collision",
        world,
        32.0,
        32.0,
    )

    body.add_child(
        shape
    )

    return body


def test_tree_root():
    world = World()

    root = Node(
        "Root",
        world,
    )

    parent = Node(
        "Parent",
        world,
    )

    child = Node(
        "Child",
        world,
    )

    root.add_child(
        parent
    )

    parent.add_child(
        child
    )

    assert child.tree_root is root


def test_iter_tree():
    world = World()

    root = Node(
        "Root",
        world,
    )

    a = Node(
        "A",
        world,
    )

    b = Node(
        "B",
        world,
    )

    root.add_child(
        a
    )

    a.add_child(
        b
    )

    assert tuple(
        root.iter_tree()
    ) == (
        root,
        a,
        b,
    )


def test_character_finds_static_body():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    wall = create_wall(
        world
    )

    root.add_child(
        player
    )

    root.add_child(
        wall
    )

    wall.transform.x = 32.0

    player.velocity.x = 100.0

    result = player.move_and_slide(
        1.0
    )

    assert player.world_position == pytest.approx(
        (
            16.0,
            0.0,
        )
    )

    assert result.collided_right

    assert player.is_on_wall

    assert player.velocity.x == pytest.approx(
        0.0
    )

    assert wall in result.colliders


def test_character_slides_along_wall():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    wall = create_wall(
        world
    )

    wall_shape = (
        wall.require_collision_shape()
    )

    wall_shape.set_size(
        32.0,
        200.0,
    )

    wall.transform.x = 32.0

    root.add_child(
        player
    )

    root.add_child(
        wall
    )

    player.velocity.set(
        100.0,
        20.0,
    )

    result = player.move_and_slide(
        1.0
    )

    assert result.collided_right

    assert player.world_position == pytest.approx(
        (
            16.0,
            20.0,
        )
    )

    assert player.velocity.x == pytest.approx(
        0.0
    )

    assert player.velocity.y == pytest.approx(
        20.0
    )


def test_character_collides_with_character():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world,
        "Player",
    )

    npc = create_character(
        world,
        "NPC",
    )

    root.add_child(
        player
    )

    root.add_child(
        npc
    )

    npc.transform.x = 32.0

    player.velocity.x = 100.0

    result = player.move_and_slide(
        1.0
    )

    assert result.collided_right

    assert player.transform.x == pytest.approx(
        16.0
    )

    assert npc in result.colliders


def test_area_does_not_block_character():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    area = Area2D(
        "Trigger",
        world,
    )

    area_shape = CollisionShape2D(
        "Collision",
        world,
        32.0,
        32.0,
    )

    area.add_child(
        area_shape
    )

    area.transform.x = 32.0

    root.add_child(
        player
    )

    root.add_child(
        area
    )

    player.velocity.x = 100.0

    result = player.move_and_slide(
        1.0
    )

    assert not result.collided

    assert player.transform.x == pytest.approx(
        100.0
    )


def test_collision_mask_is_respected():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    wall = create_wall(
        world
    )

    wall.transform.x = 32.0

    root.add_child(
        player
    )

    root.add_child(
        wall
    )

    player.set_collision_mask(
        0
    )

    player.velocity.x = 100.0

    result = player.move_and_slide(
        1.0
    )

    assert not result.collided

    assert player.transform.x == pytest.approx(
        100.0
    )


def test_disabled_body_does_not_block():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    wall = create_wall(
        world
    )

    wall.transform.x = 32.0
    wall.collision_enabled = False

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

    assert player.transform.x == pytest.approx(
        100.0
    )


def test_disabled_shape_does_not_block():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    wall = create_wall(
        world
    )

    wall.transform.x = 32.0

    wall.require_collision_shape().disabled = True

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

    assert player.transform.x == pytest.approx(
        100.0
    )


def test_child_shape_offset_is_respected():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    wall = create_wall(
        world
    )

    player_shape = (
        player.require_collision_shape()
    )

    player_shape.transform.x = 8.0

    wall.transform.x = 40.0

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

    # Shape:
    #
    # Player body X      = 0
    # Shape offset       = 8
    # Shape width        = 16
    #
    # Shape right starts = 24
    #
    # Wall begins at 40
    #
    # Allowed movement   = 16
    #
    assert player.transform.x == pytest.approx(
        16.0
    )


def test_nested_world_position_is_respected():
    world = World()

    root = Node(
        "Root",
        world,
    )

    container = Node(
        "Container",
        world,
    )

    player = create_character(
        world
    )

    wall = create_wall(
        world
    )

    root.add_child(
        container
    )

    container.add_child(
        player
    )

    root.add_child(
        wall
    )

    container.transform.x = 100.0

    wall.transform.x = 132.0

    player.velocity.x = 100.0

    player.move_and_slide(
        1.0
    )

    assert player.world_position == pytest.approx(
        (
            116.0,
            0.0,
        )
    )