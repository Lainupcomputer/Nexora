from __future__ import annotations

import pytest

from nexora.tilemap import (
    SolidTileHit,
    TileCollision,
    TileMap,
    TileSet,
)


def create_tileset() -> TileSet:
    tileset = TileSet(
        columns=4,
        rows=4,
        tile_width=32,
        tile_height=32,
    )

    tileset.metadata(
        1
    ).solid = True

    tileset.metadata(
        3
    ).solid = True

    tileset.metadata(
        5
    ).solid = True

    return tileset


def create_map() -> TileMap:
    tilemap = TileMap(
        width=10,
        height=8,
        tile_width=32,
        tile_height=32,
    )

    tilemap.create_layer(
        "ground"
    )

    return tilemap


def create_collision() -> TileCollision:
    return TileCollision(
        create_map(),
        create_tileset(),
    )


def test_collision_creation():
    collision = create_collision()

    assert collision.tilemap.width == 10
    assert collision.tileset.tile_count == 16


def test_collision_rejects_tile_size_mismatch():
    tilemap = TileMap(
        width=4,
        height=4,
        tile_width=32,
        tile_height=32,
    )

    tileset = TileSet(
        columns=4,
        rows=4,
        tile_width=16,
        tile_height=16,
    )

    with pytest.raises(
        ValueError
    ):
        TileCollision(
            tilemap,
            tileset,
        )


def test_empty_tile_is_not_solid():
    collision = create_collision()

    assert not collision.is_solid(
        "ground",
        1,
        1,
    )


def test_non_solid_tile():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    layer.set_tile(
        2,
        3,
        2,
    )

    assert not collision.is_solid(
        "ground",
        2,
        3,
    )


def test_solid_tile():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    layer.set_tile(
        2,
        3,
        3,
    )

    assert collision.is_solid(
        "ground",
        2,
        3,
    )


def test_tile_id_query():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    layer.set_tile(
        3,
        4,
        7,
    )

    assert collision.tile_id(
        "ground",
        3,
        4,
    ) == 7


def test_world_to_tile():
    collision = create_collision()

    assert collision.world_to_tile(
        0.0,
        0.0,
    ) == (
        0,
        0,
    )

    assert collision.world_to_tile(
        31.9,
        31.9,
    ) == (
        0,
        0,
    )

    assert collision.world_to_tile(
        32.0,
        32.0,
    ) == (
        1,
        1,
    )


def test_tile_world_rect():
    collision = create_collision()

    assert collision.tile_world_rect(
        2,
        3,
    ) == pytest.approx(
        (
            64.0,
            96.0,
            32.0,
            32.0,
        )
    )


def test_tile_world_rect_outside_raises():
    collision = create_collision()

    with pytest.raises(
        IndexError
    ):
        collision.tile_world_rect(
            10,
            0,
        )


def test_tile_bounds_for_single_tile_rect():
    collision = create_collision()

    assert collision.tile_bounds_for_rect(
        32.0,
        64.0,
        32.0,
        32.0,
    ) == (
        1,
        2,
        1,
        2,
    )


def test_tile_bounds_for_rect_crossing_tiles():
    collision = create_collision()

    assert collision.tile_bounds_for_rect(
        20.0,
        20.0,
        30.0,
        30.0,
    ) == (
        0,
        0,
        1,
        1,
    )


def test_tile_bounds_exact_border_does_not_include_next_tile():
    collision = create_collision()

    assert collision.tile_bounds_for_rect(
        0.0,
        0.0,
        32.0,
        32.0,
    ) == (
        0,
        0,
        0,
        0,
    )


def test_tile_bounds_are_clamped_to_map():
    collision = create_collision()

    assert collision.tile_bounds_for_rect(
        -10.0,
        -10.0,
        50.0,
        50.0,
    ) == (
        0,
        0,
        1,
        1,
    )


def test_tile_bounds_outside_map_returns_empty_range():
    collision = create_collision()

    assert collision.tile_bounds_for_rect(
        1000.0,
        1000.0,
        20.0,
        20.0,
    ) == (
        0,
        0,
        -1,
        -1,
    )


def test_invalid_rect_width_raises():
    collision = create_collision()

    with pytest.raises(
        ValueError
    ):
        collision.tile_bounds_for_rect(
            0.0,
            0.0,
            0.0,
            20.0,
        )


def test_invalid_rect_height_raises():
    collision = create_collision()

    with pytest.raises(
        ValueError
    ):
        collision.tile_bounds_for_rect(
            0.0,
            0.0,
            20.0,
            0.0,
        )


def test_solid_tiles_in_rect():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    layer.set_tile(
        1,
        1,
        1,
    )

    layer.set_tile(
        2,
        1,
        2,
    )

    layer.set_tile(
        2,
        2,
        3,
    )

    hits = collision.solid_tiles_in_rect(
        "ground",
        32.0,
        32.0,
        64.0,
        64.0,
    )

    assert len(
        hits
    ) == 2

    assert all(
        isinstance(
            hit,
            SolidTileHit,
        )
        for hit in hits
    )

    assert [
        (
            hit.tile_x,
            hit.tile_y,
            hit.tile_id,
        )
        for hit in hits
    ] == [
        (
            1,
            1,
            1,
        ),
        (
            2,
            2,
            3,
        ),
    ]


def test_solid_hit_world_rect():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    layer.set_tile(
        3,
        2,
        1,
    )

    hit = collision.solid_tiles_in_rect(
        "ground",
        96.0,
        64.0,
        32.0,
        32.0,
    )[0]

    assert hit.world_rect == pytest.approx(
        (
            96.0,
            64.0,
            32.0,
            32.0,
        )
    )


def test_solid_tiles_outside_map_returns_empty():
    collision = create_collision()

    assert collision.solid_tiles_in_rect(
        "ground",
        1000.0,
        1000.0,
        32.0,
        32.0,
    ) == []


def test_any_solid_in_rect_false():
    collision = create_collision()

    assert not collision.any_solid_in_rect(
        "ground",
        0.0,
        0.0,
        64.0,
        64.0,
    )


def test_any_solid_in_rect_true():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    layer.set_tile(
        1,
        1,
        1,
    )

    assert collision.any_solid_in_rect(
        "ground",
        0.0,
        0.0,
        64.0,
        64.0,
    )


def test_invalid_tile_id_raises():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    layer.set_tile(
        1,
        1,
        999,
    )

    with pytest.raises(
        IndexError
    ):
        collision.is_solid(
            "ground",
            1,
            1,
        )

# ==============================================================
# AABB movement
# ==============================================================


def test_move_aabb_without_collision():
    collision = create_collision()

    result = collision.move_aabb(
        "ground",
        10.0,
        10.0,
        16.0,
        16.0,
        20.0,
        30.0,
    )

    assert result.position == pytest.approx(
        (
            30.0,
            40.0,
        )
    )

    assert result.movement == pytest.approx(
        (
            20.0,
            30.0,
        )
    )

    assert not result.collided


def test_move_aabb_right_into_wall():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    # Tile starts at x = 64.
    layer.set_tile(
        2,
        1,
        1,
    )

    result = collision.move_aabb(
        "ground",
        32.0,
        32.0,
        16.0,
        16.0,
        40.0,
        0.0,
    )

    # Wall begins at 64.
    #
    # Entity width = 16.
    #
    # Maximum left coordinate:
    #
    # 64 - 16 = 48.

    assert result.x == pytest.approx(
        48.0
    )

    assert result.y == pytest.approx(
        32.0
    )

    assert result.collided_right

    assert not result.collided_left
    assert not result.collided_top
    assert not result.collided_bottom


def test_move_aabb_left_into_wall():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    # Wall from x=32 to x=64.
    layer.set_tile(
        1,
        1,
        1,
    )

    result = collision.move_aabb(
        "ground",
        80.0,
        32.0,
        16.0,
        16.0,
        -50.0,
        0.0,
    )

    assert result.x == pytest.approx(
        64.0
    )

    assert result.collided_left

    assert not result.collided_right


def test_move_aabb_down_into_floor():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    # Floor begins at y=64.
    layer.set_tile(
        1,
        2,
        1,
    )

    result = collision.move_aabb(
        "ground",
        32.0,
        32.0,
        16.0,
        16.0,
        0.0,
        40.0,
    )

    assert result.y == pytest.approx(
        48.0
    )

    assert result.collided_bottom

    assert not result.collided_top


def test_move_aabb_up_into_ceiling():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    # Ceiling occupies y=32..64.
    layer.set_tile(
        1,
        1,
        1,
    )

    result = collision.move_aabb(
        "ground",
        32.0,
        80.0,
        16.0,
        16.0,
        0.0,
        -50.0,
    )

    assert result.y == pytest.approx(
        64.0
    )

    assert result.collided_top

    assert not result.collided_bottom


def test_move_aabb_stops_at_nearest_wall():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    layer.set_tile(
        2,
        1,
        1,
    )

    layer.set_tile(
        5,
        1,
        1,
    )

    result = collision.move_aabb(
        "ground",
        0.0,
        32.0,
        16.0,
        16.0,
        300.0,
        0.0,
    )

    assert result.x == pytest.approx(
        48.0
    )

    assert result.collided_right


def test_move_aabb_large_movement_does_not_tunnel():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    layer.set_tile(
        4,
        1,
        1,
    )

    result = collision.move_aabb(
        "ground",
        0.0,
        32.0,
        16.0,
        16.0,
        500.0,
        0.0,
    )

    # Wall begins at:
    #
    # 4 * 32 = 128
    #
    # Entity width = 16
    #
    # final x = 112

    assert result.x == pytest.approx(
        112.0
    )

    assert result.collided_right


def test_move_aabb_diagonal_collision():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    # Wall to the right.
    layer.set_tile(
        2,
        1,
        1,
    )

    # Floor below.
    layer.set_tile(
        1,
        2,
        1,
    )

    result = collision.move_aabb(
        "ground",
        32.0,
        32.0,
        16.0,
        16.0,
        40.0,
        40.0,
    )

    assert result.x == pytest.approx(
        48.0
    )

    assert result.y == pytest.approx(
        48.0
    )

    assert result.collided_right
    assert result.collided_bottom


def test_move_result_reports_applied_movement():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    layer.set_tile(
        2,
        1,
        1,
    )

    result = collision.move_aabb(
        "ground",
        32.0,
        32.0,
        16.0,
        16.0,
        100.0,
        10.0,
    )

    assert result.dx == pytest.approx(
        16.0
    )

    assert result.dy == pytest.approx(
        10.0
    )


def test_move_aabb_zero_movement():
    collision = create_collision()

    result = collision.move_aabb(
        "ground",
        20.0,
        30.0,
        16.0,
        16.0,
        0.0,
        0.0,
    )

    assert result.position == pytest.approx(
        (
            20.0,
            30.0,
        )
    )

    assert result.movement == pytest.approx(
        (
            0.0,
            0.0,
        )
    )

    assert not result.collided


def test_move_aabb_rejects_zero_width():
    collision = create_collision()

    with pytest.raises(
        ValueError
    ):
        collision.move_aabb(
            "ground",
            0.0,
            0.0,
            0.0,
            16.0,
            10.0,
            0.0,
        )


def test_move_aabb_rejects_zero_height():
    collision = create_collision()

    with pytest.raises(
        ValueError
    ):
        collision.move_aabb(
            "ground",
            0.0,
            0.0,
            16.0,
            0.0,
            0.0,
            10.0,
        )


def test_move_result_helpers():
    collision = create_collision()

    layer = collision.tilemap.require_layer(
        "ground"
    )

    layer.set_tile(
        2,
        1,
        1,
    )

    result = collision.move_aabb(
        "ground",
        32.0,
        32.0,
        16.0,
        16.0,
        100.0,
        0.0,
    )

    assert result.collided

    assert result.position == pytest.approx(
        (
            48.0,
            32.0,
        )
    )

    assert result.movement == pytest.approx(
        (
            16.0,
            0.0,
        )
    )