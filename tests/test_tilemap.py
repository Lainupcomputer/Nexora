from __future__ import annotations

import pytest

from nexora.tilemap import (
    TileLayer,
    TileMap,
)


# ==============================================================
# Helpers
# ==============================================================


def create_tilemap() -> TileMap:
    return TileMap(
        name="TestMap",
        width=10,
        height=8,
        tile_width=32,
        tile_height=16,
    )


# ==============================================================
# Construction
# ==============================================================


def test_tilemap_properties():
    tilemap = create_tilemap()

    assert tilemap.name == "TestMap"

    assert tilemap.width == 10
    assert tilemap.height == 8

    assert tilemap.tile_width == 32
    assert tilemap.tile_height == 16

    assert tilemap.size == (
        10,
        8,
    )

    assert tilemap.tile_size == (
        32,
        16,
    )


def test_tilemap_pixel_size():
    tilemap = create_tilemap()

    assert tilemap.pixel_width == 320
    assert tilemap.pixel_height == 128

    assert tilemap.pixel_size == (
        320,
        128,
    )


@pytest.mark.parametrize(
    (
        "width",
        "height",
        "tile_width",
        "tile_height",
    ),
    [
        (0, 1, 32, 32),
        (-1, 1, 32, 32),
        (1, 0, 32, 32),
        (1, -1, 32, 32),
        (1, 1, 0, 32),
        (1, 1, -1, 32),
        (1, 1, 32, 0),
        (1, 1, 32, -1),
    ],
)
def test_invalid_dimensions_rejected(
    width,
    height,
    tile_width,
    tile_height,
):
    with pytest.raises(
        ValueError
    ):
        TileMap(
            width=width,
            height=height,
            tile_width=tile_width,
            tile_height=tile_height,
        )


# ==============================================================
# Create layers
# ==============================================================


def test_create_layer():
    tilemap = create_tilemap()

    layer = tilemap.create_layer(
        "ground"
    )

    assert isinstance(
        layer,
        TileLayer,
    )

    assert layer.name == "ground"

    assert layer.size == (
        tilemap.width,
        tilemap.height,
    )

    assert tilemap.layer_count == 1


def test_create_layer_preserves_options():
    tilemap = create_tilemap()

    layer = tilemap.create_layer(
        "foreground",
        visible=False,
        enabled=False,
        opacity=0.4,
    )

    assert layer.visible is False
    assert layer.enabled is False

    assert layer.opacity == pytest.approx(
        0.4
    )


def test_duplicate_layer_name_rejected():
    tilemap = create_tilemap()

    tilemap.create_layer(
        "ground"
    )

    with pytest.raises(
        ValueError
    ):
        tilemap.create_layer(
            "ground"
        )


# ==============================================================
# Add existing layer
# ==============================================================


def test_add_existing_layer():
    tilemap = create_tilemap()

    layer = TileLayer(
        "objects",
        width=10,
        height=8,
    )

    tilemap.add_layer(
        layer
    )

    assert tilemap.get_layer(
        "objects"
    ) is layer


def test_add_layer_wrong_size_rejected():
    tilemap = create_tilemap()

    layer = TileLayer(
        "bad",
        width=5,
        height=5,
    )

    with pytest.raises(
        ValueError
    ):
        tilemap.add_layer(
            layer
        )


def test_add_non_layer_rejected():
    tilemap = create_tilemap()

    with pytest.raises(
        TypeError
    ):
        tilemap.add_layer(
            object()
        )


# ==============================================================
# Layer lookup
# ==============================================================


def test_get_layer():
    tilemap = create_tilemap()

    layer = tilemap.create_layer(
        "ground"
    )

    assert tilemap.get_layer(
        "ground"
    ) is layer


def test_get_missing_layer_returns_none():
    tilemap = create_tilemap()

    assert tilemap.get_layer(
        "missing"
    ) is None


def test_require_layer():
    tilemap = create_tilemap()

    layer = tilemap.create_layer(
        "ground"
    )

    assert tilemap.require_layer(
        "ground"
    ) is layer


def test_require_missing_layer_raises():
    tilemap = create_tilemap()

    with pytest.raises(
        KeyError
    ):
        tilemap.require_layer(
            "missing"
        )


def test_has_layer():
    tilemap = create_tilemap()

    tilemap.create_layer(
        "ground"
    )

    assert tilemap.has_layer(
        "ground"
    )

    assert not tilemap.has_layer(
        "missing"
    )


# ==============================================================
# Layer order
# ==============================================================


def test_layer_order():
    tilemap = create_tilemap()

    ground = tilemap.create_layer(
        "ground"
    )

    objects = tilemap.create_layer(
        "objects"
    )

    foreground = tilemap.create_layer(
        "foreground"
    )

    assert tilemap.layers == (
        ground,
        objects,
        foreground,
    )

    assert tilemap.layer_names == (
        "ground",
        "objects",
        "foreground",
    )


def test_create_layer_at_index():
    tilemap = create_tilemap()

    tilemap.create_layer(
        "ground"
    )

    tilemap.create_layer(
        "foreground"
    )

    tilemap.create_layer(
        "objects",
        index=1,
    )

    assert tilemap.layer_names == (
        "ground",
        "objects",
        "foreground",
    )


def test_layer_at():
    tilemap = create_tilemap()

    ground = tilemap.create_layer(
        "ground"
    )

    objects = tilemap.create_layer(
        "objects"
    )

    assert tilemap.layer_at(
        0
    ) is ground

    assert tilemap.layer_at(
        1
    ) is objects

    assert tilemap.layer_at(
        -1
    ) is objects


def test_layer_at_invalid_index_raises():
    tilemap = create_tilemap()

    tilemap.create_layer(
        "ground"
    )

    with pytest.raises(
        IndexError
    ):
        tilemap.layer_at(
            5
        )


def test_layer_index():
    tilemap = create_tilemap()

    tilemap.create_layer(
        "ground"
    )

    tilemap.create_layer(
        "objects"
    )

    assert tilemap.layer_index(
        "objects"
    ) == 1


# ==============================================================
# Moving layers
# ==============================================================


def test_move_layer():
    tilemap = create_tilemap()

    tilemap.create_layer(
        "ground"
    )

    tilemap.create_layer(
        "objects"
    )

    tilemap.create_layer(
        "foreground"
    )

    tilemap.move_layer(
        "foreground",
        0,
    )

    assert tilemap.layer_names == (
        "foreground",
        "ground",
        "objects",
    )


def test_move_layer_up():
    tilemap = create_tilemap()

    tilemap.create_layer(
        "ground"
    )

    tilemap.create_layer(
        "objects"
    )

    tilemap.create_layer(
        "foreground"
    )

    tilemap.move_layer_up(
        "ground"
    )

    assert tilemap.layer_names == (
        "objects",
        "ground",
        "foreground",
    )


def test_move_layer_down():
    tilemap = create_tilemap()

    tilemap.create_layer(
        "ground"
    )

    tilemap.create_layer(
        "objects"
    )

    tilemap.create_layer(
        "foreground"
    )

    tilemap.move_layer_down(
        "foreground"
    )

    assert tilemap.layer_names == (
        "ground",
        "foreground",
        "objects",
    )


def test_move_layer_to_top():
    tilemap = create_tilemap()

    tilemap.create_layer(
        "ground"
    )

    tilemap.create_layer(
        "objects"
    )

    tilemap.create_layer(
        "foreground"
    )

    tilemap.move_layer_to_top(
        "ground"
    )

    assert tilemap.layer_names == (
        "objects",
        "foreground",
        "ground",
    )


def test_move_layer_to_bottom():
    tilemap = create_tilemap()

    tilemap.create_layer(
        "ground"
    )

    tilemap.create_layer(
        "objects"
    )

    tilemap.create_layer(
        "foreground"
    )

    tilemap.move_layer_to_bottom(
        "foreground"
    )

    assert tilemap.layer_names == (
        "foreground",
        "ground",
        "objects",
    )


# ==============================================================
# Remove
# ==============================================================


def test_remove_layer_by_name():
    tilemap = create_tilemap()

    layer = tilemap.create_layer(
        "objects"
    )

    removed = tilemap.remove_layer(
        "objects"
    )

    assert removed is layer

    assert not tilemap.has_layer(
        "objects"
    )


def test_remove_layer_by_object():
    tilemap = create_tilemap()

    layer = tilemap.create_layer(
        "objects"
    )

    removed = tilemap.remove_layer(
        layer
    )

    assert removed is layer


def test_remove_missing_layer_returns_none():
    tilemap = create_tilemap()

    assert tilemap.remove_layer(
        "missing"
    ) is None


def test_clear_layers():
    tilemap = create_tilemap()

    tilemap.create_layer(
        "ground"
    )

    tilemap.create_layer(
        "objects"
    )

    tilemap.clear_layers()

    assert tilemap.layer_count == 0

    assert tilemap.layers == ()


# ==============================================================
# Coordinates
# ==============================================================


def test_contains():
    tilemap = create_tilemap()

    assert tilemap.contains(
        0,
        0,
    )

    assert tilemap.contains(
        9,
        7,
    )

    assert not tilemap.contains(
        -1,
        0,
    )

    assert not tilemap.contains(
        10,
        0,
    )

    assert not tilemap.contains(
        0,
        8,
    )


def test_tile_to_world():
    tilemap = create_tilemap()

    assert tilemap.tile_to_world(
        0,
        0,
    ) == pytest.approx(
        (
            16.0,
            8.0,
        )
    )

    assert tilemap.tile_to_world(
        2,
        3,
    ) == pytest.approx(
        (
            80.0,
            56.0,
        )
    )


def test_tile_to_world_outside_raises():
    tilemap = create_tilemap()

    with pytest.raises(
        IndexError
    ):
        tilemap.tile_to_world(
            10,
            0,
        )


def test_world_to_tile():
    tilemap = create_tilemap()

    assert tilemap.world_to_tile(
        0.0,
        0.0,
    ) == (
        0,
        0,
    )

    assert tilemap.world_to_tile(
        31.0,
        15.0,
    ) == (
        0,
        0,
    )

    assert tilemap.world_to_tile(
        32.0,
        16.0,
    ) == (
        1,
        1,
    )

    assert tilemap.world_to_tile(
        95.0,
        63.0,
    ) == (
        2,
        3,
    )


# ==============================================================
# Collection API
# ==============================================================


def test_len():
    tilemap = create_tilemap()

    assert len(
        tilemap
    ) == 0

    tilemap.create_layer(
        "ground"
    )

    assert len(
        tilemap
    ) == 1


def test_contains_layer_name():
    tilemap = create_tilemap()

    tilemap.create_layer(
        "ground"
    )

    assert "ground" in tilemap
    assert "missing" not in tilemap


def test_iteration():
    tilemap = create_tilemap()

    ground = tilemap.create_layer(
        "ground"
    )

    objects = tilemap.create_layer(
        "objects"
    )

    assert list(
        tilemap
    ) == [
        ground,
        objects,
    ]