from __future__ import annotations

import pytest

from nexora.ecs.world import World
from nexora.nodes import (
    Body2D,
    CharacterBody2D,
    CollisionShape2D,
    Vector2,
)

from nexora.tilemap import (
    TileCollision,
    TileMap,
    TileSet,
)


def create_collision() -> TileCollision:
    tileset = TileSet(
        columns=4,
        rows=4,
        tile_width=32,
        tile_height=32,
    )

    tileset.metadata(
        1
    ).solid = True

    tilemap = TileMap(
        width=10,
        height=10,
        tile_width=32,
        tile_height=32,
    )

    tilemap.create_layer(
        "collision"
    )

    return TileCollision(
        tilemap,
        tileset,
    )


def create_body() -> CharacterBody2D:
    world = World()

    body = CharacterBody2D(
        "Player",
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


def test_vector2_defaults():
    vector = Vector2()

    assert vector.tuple == (
        0.0,
        0.0,
    )


def test_vector2_set():
    vector = Vector2()

    vector.set(
        10.0,
        20.0,
    )

    assert vector.tuple == pytest.approx(
        (
            10.0,
            20.0,
        )
    )


def test_vector2_clear():
    vector = Vector2(
        10.0,
        20.0,
    )

    vector.clear()

    assert vector.tuple == (
        0.0,
        0.0,
    )


def test_character_body_is_body():
    body = create_body()

    assert isinstance(
        body,
        Body2D,
    )


def test_body_defaults():
    body = create_body()

    assert body.velocity.tuple == (
        0.0,
        0.0,
    )

    assert not body.is_on_floor
    assert not body.is_on_ceiling
    assert not body.is_on_wall

    assert body.last_collision is None


def test_body_has_collision_shape():
    body = create_body()

    shape = (
        body.primary_collision_shape
    )

    assert shape is not None

    assert shape.width == pytest.approx(
        16.0
    )

    assert shape.height == pytest.approx(
        16.0
    )


def test_move_without_collision():
    collision = create_collision()
    body = create_body()

    body.transform.x = 10.0
    body.transform.y = 20.0

    body.velocity.set(
        100.0,
        50.0,
    )

    result = body.move_and_slide(
        collision,
        "collision",
        0.5,
    )

    assert body.transform.x == pytest.approx(
        60.0
    )

    assert body.transform.y == pytest.approx(
        45.0
    )

    assert result.movement == pytest.approx(
        (
            50.0,
            25.0,
        )
    )

    assert body.velocity.tuple == pytest.approx(
        (
            100.0,
            50.0,
        )
    )


def test_collision_shape_offset_moves_correctly():
    collision = create_collision()
    body = create_body()

    shape = (
        body.require_collision_shape()
    )

    shape.transform.x = 8.0
    shape.transform.y = 12.0

    body.transform.x = 100.0
    body.transform.y = 50.0

    body.velocity.set(
        20.0,
        10.0,
    )

    body.move_and_slide(
        collision,
        "collision",
        1.0,
    )

    assert body.world_position == pytest.approx(
        (
            120.0,
            60.0,
        )
    )

    assert shape.world_position == pytest.approx(
        (
            128.0,
            72.0,
        )
    )


def test_move_into_right_wall():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "collision"
    )

    layer.set_tile(
        2,
        1,
        1,
    )

    body = create_body()

    body.transform.x = 32.0
    body.transform.y = 32.0

    body.velocity.x = 100.0

    body.move_and_slide(
        collision,
        "collision",
        1.0,
    )

    assert body.transform.x == pytest.approx(
        48.0
    )

    assert body.collided_right
    assert body.is_on_wall

    assert body.velocity.x == 0.0


def test_move_into_left_wall():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "collision"
    )

    layer.set_tile(
        1,
        1,
        1,
    )

    body = create_body()

    body.transform.x = 80.0
    body.transform.y = 32.0

    body.velocity.x = -100.0

    body.move_and_slide(
        collision,
        "collision",
        1.0,
    )

    assert body.transform.x == pytest.approx(
        64.0
    )

    assert body.collided_left
    assert body.is_on_wall

    assert body.velocity.x == 0.0


def test_move_onto_floor():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "collision"
    )

    layer.set_tile(
        1,
        2,
        1,
    )

    body = create_body()

    body.transform.x = 32.0
    body.transform.y = 32.0

    body.velocity.y = 100.0

    body.move_and_slide(
        collision,
        "collision",
        1.0,
    )

    assert body.transform.y == pytest.approx(
        48.0
    )

    assert body.is_on_floor
    assert body.velocity.y == 0.0


def test_move_into_ceiling():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "collision"
    )

    layer.set_tile(
        1,
        1,
        1,
    )

    body = create_body()

    body.transform.x = 32.0
    body.transform.y = 80.0

    body.velocity.y = -100.0

    body.move_and_slide(
        collision,
        "collision",
        1.0,
    )

    assert body.transform.y == pytest.approx(
        64.0
    )

    assert body.is_on_ceiling
    assert body.velocity.y == 0.0


def test_move_and_collide():
    collision = create_collision()
    body = create_body()

    result = body.move_and_collide(
        collision,
        "collision",
        20.0,
        10.0,
    )

    assert body.world_position == pytest.approx(
        (
            20.0,
            10.0,
        )
    )

    assert result.movement == pytest.approx(
        (
            20.0,
            10.0,
        )
    )


def test_movement_requires_shape():
    body = CharacterBody2D(
        "Player",
        World(),
    )

    collision = create_collision()

    with pytest.raises(
        RuntimeError
    ):
        body.move_and_slide(
            collision,
            "collision",
            1.0,
        )


def test_disabled_shape_cannot_be_used():
    body = create_body()

    shape = (
        body.require_collision_shape()
    )

    shape.disabled = True

    collision = create_collision()

    with pytest.raises(
        RuntimeError
    ):
        body.move_and_slide(
            collision,
            "collision",
            1.0,
        )