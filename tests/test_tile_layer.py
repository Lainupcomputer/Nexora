from __future__ import annotations

import pytest

from nexora.tilemap import (
    EMPTY_TILE,
    TileLayer,
)


def create_layer() -> TileLayer:
    return TileLayer(
        "Ground",
        width=5,
        height=4,
    )


# ==============================================================
# Construction
# ==============================================================


def test_layer_properties():
    layer = create_layer()

    assert layer.name == "Ground"

    assert layer.width == 5
    assert layer.height == 4

    assert layer.size == (
        5,
        4,
    )

    assert layer.cell_count == 20

    assert layer.visible is True
    assert layer.enabled is True

    assert layer.opacity == pytest.approx(
        1.0
    )


def test_empty_name_rejected():
    with pytest.raises(
        ValueError
    ):
        TileLayer(
            "",
            width=4,
            height=4,
        )


@pytest.mark.parametrize(
    (
        "width",
        "height",
    ),
    [
        (
            0,
            1,
        ),
        (
            -1,
            1,
        ),
        (
            1,
            0,
        ),
        (
            1,
            -1,
        ),
    ],
)
def test_invalid_size_rejected(
    width,
    height,
):
    with pytest.raises(
        ValueError
    ):
        TileLayer(
            "Layer",
            width=width,
            height=height,
        )


def test_initial_tiles_are_empty():
    layer = create_layer()

    assert all(
        tile == EMPTY_TILE
        for tile in layer.tiles
    )


# ==============================================================
# Contains
# ==============================================================


def test_contains():
    layer = create_layer()

    assert layer.contains(
        0,
        0,
    )

    assert layer.contains(
        4,
        3,
    )

    assert not layer.contains(
        -1,
        0,
    )

    assert not layer.contains(
        5,
        0,
    )

    assert not layer.contains(
        0,
        -1,
    )

    assert not layer.contains(
        0,
        4,
    )


# ==============================================================
# Get / set
# ==============================================================


def test_set_and_get_tile():
    layer = create_layer()

    layer.set_tile(
        2,
        1,
        7,
    )

    assert layer.get_tile(
        2,
        1,
    ) == 7


def test_tile_zero_is_valid():
    layer = create_layer()

    layer.set_tile(
        1,
        1,
        0,
    )

    assert layer.get_tile(
        1,
        1,
    ) == 0

    assert not layer.is_empty(
        1,
        1,
    )


def test_negative_tile_id_rejected():
    layer = create_layer()

    with pytest.raises(
        ValueError
    ):
        layer.set_tile(
            0,
            0,
            -1,
        )


def test_outside_get_raises():
    layer = create_layer()

    with pytest.raises(
        IndexError
    ):
        layer.get_tile(
            5,
            0,
        )


def test_outside_set_raises():
    layer = create_layer()

    with pytest.raises(
        IndexError
    ):
        layer.set_tile(
            0,
            4,
            1,
        )


# ==============================================================
# Clear
# ==============================================================


def test_clear_tile():
    layer = create_layer()

    layer.set_tile(
        2,
        2,
        4,
    )

    layer.clear_tile(
        2,
        2,
    )

    assert layer.get_tile(
        2,
        2,
    ) == EMPTY_TILE

    assert layer.is_empty(
        2,
        2,
    )


def test_clear_layer():
    layer = create_layer()

    layer.fill(
        3
    )

    layer.clear()

    assert layer.count_tiles() == 0

    assert all(
        tile == EMPTY_TILE
        for tile in layer.tiles
    )


# ==============================================================
# Fill
# ==============================================================


def test_fill():
    layer = create_layer()

    layer.fill(
        9
    )

    assert layer.count_tiles() == 20

    assert all(
        tile == 9
        for tile in layer.tiles
    )


def test_fill_negative_tile_rejected():
    layer = create_layer()

    with pytest.raises(
        ValueError
    ):
        layer.fill(
            -1
        )


# ==============================================================
# Rectangles
# ==============================================================


def test_fill_rect():
    layer = create_layer()

    layer.fill_rect(
        1,
        1,
        3,
        2,
        5,
    )

    expected = {
        (
            1,
            1,
        ),
        (
            2,
            1,
        ),
        (
            3,
            1,
        ),
        (
            1,
            2,
        ),
        (
            2,
            2,
        ),
        (
            3,
            2,
        ),
    }

    actual = {
        (
            x,
            y,
        )
        for (
            x,
            y,
            tile,
        ) in layer.iter_tiles()
        if tile == 5
    }

    assert actual == expected


def test_clear_rect():
    layer = create_layer()

    layer.fill(
        2
    )

    layer.clear_rect(
        1,
        1,
        2,
        2,
    )

    assert layer.is_empty(
        1,
        1,
    )

    assert layer.is_empty(
        2,
        1,
    )

    assert layer.is_empty(
        1,
        2,
    )

    assert layer.is_empty(
        2,
        2,
    )

    assert layer.count_tiles() == 16


def test_fill_rect_outside_raises():
    layer = create_layer()

    with pytest.raises(
        IndexError
    ):
        layer.fill_rect(
            4,
            3,
            2,
            2,
            1,
        )


def test_clear_rect_outside_raises():
    layer = create_layer()

    with pytest.raises(
        IndexError
    ):
        layer.clear_rect(
            4,
            3,
            2,
            2,
        )


def test_zero_width_rect_rejected():
    layer = create_layer()

    with pytest.raises(
        ValueError
    ):
        layer.fill_rect(
            0,
            0,
            0,
            1,
            1,
        )


# ==============================================================
# Iteration
# ==============================================================


def test_iter_tiles_skips_empty_by_default():
    layer = create_layer()

    layer.set_tile(
        1,
        0,
        3,
    )

    layer.set_tile(
        4,
        2,
        7,
    )

    assert list(
        layer.iter_tiles()
    ) == [
        (
            1,
            0,
            3,
        ),
        (
            4,
            2,
            7,
        ),
    ]


def test_iter_tiles_can_include_empty():
    layer = TileLayer(
        "Small",
        width=2,
        height=2,
    )

    layer.set_tile(
        0,
        0,
        5,
    )

    assert list(
        layer.iter_tiles(
            include_empty=True
        )
    ) == [
        (
            0,
            0,
            5,
        ),
        (
            1,
            0,
            EMPTY_TILE,
        ),
        (
            0,
            1,
            EMPTY_TILE,
        ),
        (
            1,
            1,
            EMPTY_TILE,
        ),
    ]


# ==============================================================
# Count / find
# ==============================================================


def test_count_tiles():
    layer = create_layer()

    layer.set_tile(
        0,
        0,
        1,
    )

    layer.set_tile(
        1,
        0,
        2,
    )

    assert layer.count_tiles() == 2


def test_find_tiles():
    layer = create_layer()

    layer.set_tile(
        0,
        0,
        4,
    )

    layer.set_tile(
        2,
        1,
        4,
    )

    layer.set_tile(
        4,
        3,
        4,
    )

    layer.set_tile(
        1,
        2,
        7,
    )

    assert layer.find_tiles(
        4
    ) == [
        (
            0,
            0,
        ),
        (
            2,
            1,
        ),
        (
            4,
            3,
        ),
    ]


# ==============================================================
# Opacity
# ==============================================================


def test_opacity_is_clamped_on_creation():
    low = TileLayer(
        "Low",
        width=1,
        height=1,
        opacity=-5.0,
    )

    high = TileLayer(
        "High",
        width=1,
        height=1,
        opacity=5.0,
    )

    assert low.opacity == pytest.approx(
        0.0
    )

    assert high.opacity == pytest.approx(
        1.0
    )


def test_set_opacity_clamps():
    layer = create_layer()

    layer.set_opacity(
        0.4
    )

    assert layer.opacity == pytest.approx(
        0.4
    )

    layer.set_opacity(
        10.0
    )

    assert layer.opacity == pytest.approx(
        1.0
    )