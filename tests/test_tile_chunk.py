from __future__ import annotations

import pytest

from nexora.tilemap import (
    EMPTY_TILE,
    TileChunk,
)


def test_chunk_defaults():
    chunk = TileChunk(
        0,
        0,
    )

    assert chunk.chunk_x == 0
    assert chunk.chunk_y == 0

    assert chunk.width == 32
    assert chunk.height == 32

    assert chunk.coordinates == (
        0,
        0,
    )

    assert chunk.tile_count == 1024
    assert len(chunk) == 1024

    assert chunk.empty
    assert chunk.non_empty_count == 0

    assert chunk.dirty


def test_chunk_accepts_custom_size():
    chunk = TileChunk(
        3,
        5,
        width=7,
        height=11,
    )

    assert chunk.coordinates == (
        3,
        5,
    )

    assert chunk.width == 7
    assert chunk.height == 11

    assert chunk.tile_count == 77


@pytest.mark.parametrize(
    (
        "chunk_x",
        "chunk_y",
        "width",
        "height",
    ),
    [
        (
            -1,
            0,
            32,
            32,
        ),
        (
            0,
            -1,
            32,
            32,
        ),
        (
            0,
            0,
            0,
            32,
        ),
        (
            0,
            0,
            32,
            0,
        ),
        (
            0,
            0,
            -1,
            32,
        ),
        (
            0,
            0,
            32,
            -1,
        ),
    ],
)
def test_chunk_rejects_invalid_values(
    chunk_x,
    chunk_y,
    width,
    height,
):
    with pytest.raises(
        ValueError
    ):
        TileChunk(
            chunk_x,
            chunk_y,
            width=width,
            height=height,
        )


def test_new_chunk_contains_empty_tiles():
    chunk = TileChunk(
        0,
        0,
        width=4,
        height=3,
    )

    for y in range(
        chunk.height
    ):
        for x in range(
            chunk.width
        ):
            assert (
                chunk.get_tile(
                    x,
                    y,
                )
                == EMPTY_TILE
            )


def test_contains():
    chunk = TileChunk(
        0,
        0,
        width=4,
        height=3,
    )

    assert chunk.contains(
        0,
        0,
    )

    assert chunk.contains(
        3,
        2,
    )

    assert not chunk.contains(
        -1,
        0,
    )

    assert not chunk.contains(
        4,
        0,
    )

    assert not chunk.contains(
        0,
        3,
    )


def test_out_of_bounds_access_raises():
    chunk = TileChunk(
        0,
        0,
        width=4,
        height=4,
    )

    with pytest.raises(
        IndexError
    ):
        chunk.get_tile(
            4,
            0,
        )

    with pytest.raises(
        IndexError
    ):
        chunk.set_tile(
            -1,
            0,
            1,
        )


def test_set_and_get_tile():
    chunk = TileChunk(
        0,
        0,
    )

    changed = chunk.set_tile(
        4,
        7,
        12,
    )

    assert changed

    assert (
        chunk.get_tile(
            4,
            7,
        )
        == 12
    )

    assert not chunk.empty
    assert chunk.non_empty_count == 1


def test_setting_same_tile_does_not_change_chunk():
    chunk = TileChunk(
        0,
        0,
    )

    chunk.set_tile(
        1,
        2,
        5,
    )

    chunk.mark_clean()

    changed = chunk.set_tile(
        1,
        2,
        5,
    )

    assert not changed
    assert not chunk.dirty


def test_changed_tile_marks_chunk_dirty():
    chunk = TileChunk(
        0,
        0,
    )

    chunk.mark_clean()

    assert not chunk.dirty

    chunk.set_tile(
        2,
        3,
        8,
    )

    assert chunk.dirty


def test_non_empty_count_tracks_changes():
    chunk = TileChunk(
        0,
        0,
    )

    chunk.set_tile(
        0,
        0,
        1,
    )

    chunk.set_tile(
        1,
        0,
        2,
    )

    assert chunk.non_empty_count == 2

    # Replacing one non-empty tile with another must not
    # change the count.

    chunk.set_tile(
        0,
        0,
        7,
    )

    assert chunk.non_empty_count == 2

    chunk.clear_tile(
        1,
        0,
    )

    assert chunk.non_empty_count == 1


def test_clear_tile():
    chunk = TileChunk(
        0,
        0,
    )

    chunk.set_tile(
        5,
        5,
        10,
    )

    chunk.mark_clean()

    changed = chunk.clear_tile(
        5,
        5,
    )

    assert changed

    assert (
        chunk.get_tile(
            5,
            5,
        )
        == EMPTY_TILE
    )

    assert chunk.empty
    assert chunk.dirty


def test_clear_empty_tile_does_nothing():
    chunk = TileChunk(
        0,
        0,
    )

    chunk.mark_clean()

    changed = chunk.clear_tile(
        1,
        1,
    )

    assert not changed
    assert not chunk.dirty


def test_clear_chunk():
    chunk = TileChunk(
        0,
        0,
        width=4,
        height=4,
    )

    chunk.set_tile(
        0,
        0,
        1,
    )

    chunk.set_tile(
        3,
        3,
        2,
    )

    chunk.mark_clean()

    changed = chunk.clear()

    assert changed

    assert chunk.empty
    assert chunk.non_empty_count == 0
    assert chunk.dirty

    assert all(
        tile_id == EMPTY_TILE
        for (
            _,
            _,
            tile_id,
        ) in chunk.iter_tiles()
    )


def test_clear_empty_chunk_does_not_mark_dirty():
    chunk = TileChunk(
        0,
        0,
    )

    chunk.mark_clean()

    changed = chunk.clear()

    assert not changed
    assert not chunk.dirty


def test_mark_dirty_and_clean():
    chunk = TileChunk(
        0,
        0,
    )

    assert chunk.dirty

    chunk.mark_clean()

    assert not chunk.dirty

    chunk.mark_dirty()

    assert chunk.dirty


def test_iter_tiles():
    chunk = TileChunk(
        0,
        0,
        width=2,
        height=2,
    )

    chunk.set_tile(
        0,
        0,
        1,
    )

    chunk.set_tile(
        1,
        1,
        9,
    )

    assert list(
        chunk.iter_tiles()
    ) == [
        (
            0,
            0,
            1,
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
            9,
        ),
    ]


def test_iter_non_empty():
    chunk = TileChunk(
        2,
        4,
        width=3,
        height=3,
    )

    chunk.set_tile(
        0,
        1,
        4,
    )

    chunk.set_tile(
        2,
        2,
        8,
    )

    assert list(
        chunk.iter_non_empty()
    ) == [
        (
            0,
            1,
            4,
        ),
        (
            2,
            2,
            8,
        ),
    ]


def test_repr():
    chunk = TileChunk(
        2,
        3,
        width=16,
        height=8,
    )

    text = repr(
        chunk
    )

    assert "TileChunk" in text
    assert "chunk_x=2" in text
    assert "chunk_y=3" in text
    assert "width=16" in text
    assert "height=8" in text