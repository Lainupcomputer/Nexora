from __future__ import annotations

import pytest

from nexora.ecs.world import World
from nexora.nodes import (
    CharacterBody2D,
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
    body = CharacterBody2D(
        "Player",
        World(),
    )

    body.set_collision_size(
        16.0,
        16.0,
    )

    return body


def test_vector2_defaults():
    vector = Vector2()

    assert vector.x == 0.0
    assert vector.y == 0.0

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


def test_body_defaults():
    body = create_body()

    assert body.velocity.tuple == (
        0.0,
        0.0,
    )

    assert body.collision_size == (
        16.0,
        16.0,
    )

    assert not body.is_on_floor
    assert not body.is_on_ceiling
    assert not body.is_on_wall

    assert body.last_collision is None


def test_set_collision_size():
    body = create_body()

    body.set_collision_size(
        20.0,
        30.0,
    )

    assert body.collision_size == (
        20.0,
        30.0,
    )


def test_invalid_collision_width():
    body = create_body()

    with pytest.raises(
        ValueError
    ):
        body.set_collision_size(
            0.0,
            20.0,
        )


def test_invalid_collision_height():
    body = create_body()

    with pytest.raises(
        ValueError
    ):
        body.set_collision_size(
            20.0,
            0.0,
        )


def test_collision_offset():
    body = create_body()

    body.transform.x = 100.0
    body.transform.y = 50.0

    body.set_collision_offset(
        5.0,
        8.0,
    )

    assert body.collision_position == pytest.approx(
        (
            105.0,
            58.0,
        )
    )


def test_collision_rect():
    body = create_body()

    body.transform.x = 10.0
    body.transform.y = 20.0

    assert body.collision_rect == pytest.approx(
        (
            10.0,
            20.0,
            16.0,
            16.0,
        )
    )


def test_move_and_slide_without_collision():
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

    assert not body.is_on_floor
    assert not body.is_on_wall


def test_move_and_slide_into_right_wall():
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


def test_move_and_slide_into_left_wall():
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


def test_move_and_slide_onto_floor():
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

    assert not body.is_on_ceiling

    assert body.velocity.y == 0.0


def test_move_and_slide_into_ceiling():
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
    assert not body.is_on_floor

    assert body.velocity.y == 0.0


def test_move_and_slide_diagonal():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "collision"
    )

    layer.set_tile(
        2,
        1,
        1,
    )

    layer.set_tile(
        1,
        2,
        1,
    )

    body = create_body()

    body.transform.x = 32.0
    body.transform.y = 32.0

    body.velocity.set(
        100.0,
        100.0,
    )

    body.move_and_slide(
        collision,
        "collision",
        1.0,
    )

    assert body.transform.x == pytest.approx(
        48.0
    )

    assert body.transform.y == pytest.approx(
        48.0
    )

    assert body.is_on_wall
    assert body.is_on_floor

    assert body.velocity.tuple == (
        0.0,
        0.0,
    )


def test_move_and_slide_preserves_unblocked_axis():
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

    body.velocity.set(
        100.0,
        25.0,
    )

    body.move_and_slide(
        collision,
        "collision",
        1.0,
    )

    assert body.transform.x == pytest.approx(
        48.0
    )

    assert body.transform.y == pytest.approx(
        57.0
    )

    assert body.velocity.x == 0.0

    assert body.velocity.y == pytest.approx(
        25.0
    )


def test_move_and_slide_uses_collision_offset():
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

    body.transform.x = 27.0
    body.transform.y = 32.0

    body.set_collision_offset(
        5.0,
        0.0,
    )

    body.velocity.x = 100.0

    body.move_and_slide(
        collision,
        "collision",
        1.0,
    )

    # Collision rectangle stops at x=48.
    #
    # Body transform must therefore be:
    #
    # 48 - offset 5 = 43.

    assert body.transform.x == pytest.approx(
        43.0
    )

    assert body.collided_right


def test_negative_delta_time_rejected():
    collision = create_collision()
    body = create_body()

    with pytest.raises(
        ValueError
    ):
        body.move_and_slide(
            collision,
            "collision",
            -1.0,
        )


def test_zero_delta_time_does_not_move():
    collision = create_collision()
    body = create_body()

    body.transform.x = 10.0
    body.transform.y = 20.0

    body.velocity.set(
        100.0,
        100.0,
    )

    body.move_and_slide(
        collision,
        "collision",
        0.0,
    )

    assert body.transform.x == pytest.approx(
        10.0
    )

    assert body.transform.y == pytest.approx(
        20.0
    )


def test_move_and_collide():
    collision = create_collision()
    body = create_body()

    result = body.move_and_collide(
        collision,
        "collision",
        20.0,
        30.0,
    )

    assert body.transform.x == pytest.approx(
        20.0
    )

    assert body.transform.y == pytest.approx(
        30.0
    )

    assert result.movement == pytest.approx(
        (
            20.0,
            30.0,
        )
    )


def test_last_collision_is_set():
    collision = create_collision()
    body = create_body()

    result = body.move_and_collide(
        collision,
        "collision",
        10.0,
        0.0,
    )

    assert body.last_collision is result


def test_collision_state_resets_between_moves():
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

    assert body.is_on_wall

    body.velocity.clear()

    body.move_and_slide(
        collision,
        "collision",
        0.0,
    )

    assert not body.is_on_wall
    assert not body.is_on_floor
    assert not body.is_on_ceiling