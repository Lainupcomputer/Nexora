from __future__ import annotations

import pytest

from nexora.tilemap import (
    TileRegion,
    TileSet,
)


def create_tileset() -> TileSet:
    return TileSet(
        name="TestTiles",
        columns=4,
        rows=3,
        tile_width=32,
        tile_height=16,
    )


def test_tileset_properties():
    tileset = create_tileset()

    assert tileset.name == "TestTiles"

    assert tileset.columns == 4
    assert tileset.rows == 3

    assert tileset.tile_width == 32
    assert tileset.tile_height == 16


def test_tileset_tile_count():
    tileset = create_tileset()

    assert tileset.tile_count == 12


def test_tileset_tile_size():
    tileset = create_tileset()

    assert tileset.tile_size == (
        32,
        16,
    )


def test_tileset_texture_size():
    tileset = create_tileset()

    assert tileset.texture_size == (
        128,
        48,
    )


@pytest.mark.parametrize(
    (
        "columns",
        "rows",
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
def test_tileset_rejects_invalid_dimensions(
    columns,
    rows,
    tile_width,
    tile_height,
):
    with pytest.raises(
        ValueError
    ):
        TileSet(
            columns=columns,
            rows=rows,
            tile_width=tile_width,
            tile_height=tile_height,
        )


def test_contains():
    tileset = create_tileset()

    assert tileset.contains(
        0
    )

    assert tileset.contains(
        11
    )

    assert not tileset.contains(
        -1
    )

    assert not tileset.contains(
        12
    )


def test_index_from_cell():
    tileset = create_tileset()

    assert tileset.index(
        0,
        0,
    ) == 0

    assert tileset.index(
        3,
        0,
    ) == 3

    assert tileset.index(
        0,
        1,
    ) == 4

    assert tileset.index(
        2,
        2,
    ) == 10


def test_cell_from_index():
    tileset = create_tileset()

    assert tileset.cell(
        0
    ) == (
        0,
        0,
    )

    assert tileset.cell(
        4
    ) == (
        0,
        1,
    )

    assert tileset.cell(
        10
    ) == (
        2,
        2,
    )


def test_index_cell_roundtrip():
    tileset = create_tileset()

    for index in range(
        tileset.tile_count
    ):
        column, row = (
            tileset.cell(
                index
            )
        )

        assert tileset.index(
            column,
            row,
        ) == index


def test_invalid_index_raises():
    tileset = create_tileset()

    with pytest.raises(
        IndexError
    ):
        tileset.cell(
            -1
        )

    with pytest.raises(
        IndexError
    ):
        tileset.cell(
            12
        )


def test_invalid_cell_raises():
    tileset = create_tileset()

    with pytest.raises(
        IndexError
    ):
        tileset.index(
            -1,
            0,
        )

    with pytest.raises(
        IndexError
    ):
        tileset.index(
            4,
            0,
        )

    with pytest.raises(
        IndexError
    ):
        tileset.index(
            0,
            -1,
        )

    with pytest.raises(
        IndexError
    ):
        tileset.index(
            0,
            3,
        )


def test_first_tile_uv():
    tileset = create_tileset()

    assert tileset.uv(
        0
    ) == pytest.approx(
        (
            0.0,
            0.0,
            0.25,
            1.0 / 3.0,
        )
    )


def test_middle_tile_uv():
    tileset = create_tileset()

    assert tileset.uv(
        6
    ) == pytest.approx(
        (
            0.5,
            1.0 / 3.0,
            0.25,
            1.0 / 3.0,
        )
    )


def test_last_tile_uv():
    tileset = create_tileset()

    assert tileset.uv(
        11
    ) == pytest.approx(
        (
            0.75,
            2.0 / 3.0,
            0.25,
            1.0 / 3.0,
        )
    )


def test_uv_at():
    tileset = create_tileset()

    assert tileset.uv_at(
        2,
        1,
    ) == pytest.approx(
        tileset.uv(
            6
        )
    )


def test_region():
    tileset = create_tileset()

    region = tileset.region(
        6
    )

    assert isinstance(
        region,
        TileRegion,
    )

    assert region.index == 6
    assert region.column == 2
    assert region.row == 1

    assert region.uv == pytest.approx(
        (
            0.5,
            1.0 / 3.0,
            0.25,
            1.0 / 3.0,
        )
    )


def test_region_at():
    tileset = create_tileset()

    region = tileset.region_at(
        3,
        2,
    )

    assert region.index == 11
    assert region.column == 3
    assert region.row == 2


def test_pixel_rect():
    tileset = create_tileset()

    assert tileset.pixel_rect(
        0
    ) == (
        0,
        0,
        32,
        16,
    )

    assert tileset.pixel_rect(
        6
    ) == (
        64,
        16,
        32,
        16,
    )

    assert tileset.pixel_rect(
        11
    ) == (
        96,
        32,
        32,
        16,
    )