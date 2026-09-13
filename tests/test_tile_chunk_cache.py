from __future__ import annotations

import pytest

from nexora.tilemap import (
    CachedTile,
    TileChunk,
    TileChunkRenderCache,
    TileSet,
)


def create_tileset() -> TileSet:
    return TileSet(
        columns=4,
        rows=4,
        tile_width=64,
        tile_height=64,
    )


def test_cache_starts_invalid():
    chunk = TileChunk(
        0,
        0,
    )

    cache = TileChunkRenderCache(
        chunk
    )

    assert not cache.valid
    assert cache.tiles == ()
    assert cache.tile_count == 0
    assert cache.build_count == 0


def test_cache_builds_non_empty_tiles():
    chunk = TileChunk(
        0,
        0,
        width=4,
        height=4,
    )

    chunk.set_tile(
        1,
        2,
        3,
    )

    chunk.set_tile(
        3,
        3,
        7,
    )

    tileset = create_tileset()

    cache = TileChunkRenderCache(
        chunk
    )

    tiles = cache.get(
        tileset
    )

    assert len(
        tiles
    ) == 2

    assert tiles[0].x == 1
    assert tiles[0].y == 2
    assert tiles[0].tile_id == 3

    assert tiles[1].x == 3
    assert tiles[1].y == 3
    assert tiles[1].tile_id == 7

    assert cache.valid
    assert not chunk.dirty

    assert cache.build_count == 1


def test_cached_tile_contains_uv():
    chunk = TileChunk(
        0,
        0,
    )

    chunk.set_tile(
        2,
        4,
        5,
    )

    tileset = create_tileset()

    cache = TileChunkRenderCache(
        chunk
    )

    tile = cache.get(
        tileset
    )[0]

    assert isinstance(
        tile,
        CachedTile,
    )

    assert tile.uv == pytest.approx(
        tileset.uv(
            5
        )
    )


def test_cache_is_reused_when_chunk_did_not_change():
    chunk = TileChunk(
        0,
        0,
    )

    chunk.set_tile(
        1,
        1,
        2,
    )

    tileset = create_tileset()

    cache = TileChunkRenderCache(
        chunk
    )

    first = cache.get(
        tileset
    )

    second = cache.get(
        tileset
    )

    assert first is second

    assert cache.build_count == 1
    assert cache.valid


def test_cache_rebuilds_when_chunk_changes():
    chunk = TileChunk(
        0,
        0,
    )

    chunk.set_tile(
        1,
        1,
        2,
    )

    tileset = create_tileset()

    cache = TileChunkRenderCache(
        chunk
    )

    first = cache.get(
        tileset
    )

    assert cache.build_count == 1

    chunk.set_tile(
        2,
        2,
        3,
    )

    assert chunk.dirty
    assert not cache.valid

    second = cache.get(
        tileset
    )

    assert second is not first

    assert len(
        second
    ) == 2

    assert cache.build_count == 2
    assert cache.valid
    assert not chunk.dirty


def test_setting_same_tile_does_not_rebuild_cache():
    chunk = TileChunk(
        0,
        0,
    )

    chunk.set_tile(
        1,
        1,
        4,
    )

    tileset = create_tileset()

    cache = TileChunkRenderCache(
        chunk
    )

    first = cache.get(
        tileset
    )

    assert cache.build_count == 1

    changed = chunk.set_tile(
        1,
        1,
        4,
    )

    assert not changed
    assert not chunk.dirty

    second = cache.get(
        tileset
    )

    assert second is first
    assert cache.build_count == 1


def test_cache_rebuilds_after_tile_is_cleared():
    chunk = TileChunk(
        0,
        0,
    )

    chunk.set_tile(
        1,
        1,
        4,
    )

    tileset = create_tileset()

    cache = TileChunkRenderCache(
        chunk
    )

    cache.get(
        tileset
    )

    assert cache.tile_count == 1

    chunk.clear_tile(
        1,
        1,
    )

    tiles = cache.get(
        tileset
    )

    assert tiles == ()
    assert cache.tile_count == 0
    assert cache.build_count == 2


def test_empty_chunk_can_be_cached():
    chunk = TileChunk(
        0,
        0,
    )

    tileset = create_tileset()

    cache = TileChunkRenderCache(
        chunk
    )

    tiles = cache.get(
        tileset
    )

    assert tiles == ()

    assert cache.valid
    assert not chunk.dirty

    assert cache.build_count == 1


def test_manual_invalidate_forces_rebuild():
    chunk = TileChunk(
        0,
        0,
    )

    chunk.set_tile(
        0,
        0,
        1,
    )

    tileset = create_tileset()

    cache = TileChunkRenderCache(
        chunk
    )

    first = cache.get(
        tileset
    )

    cache.invalidate()

    assert not cache.valid

    second = cache.get(
        tileset
    )

    assert second is not first
    assert cache.build_count == 2


def test_clear_invalidates_cache():
    chunk = TileChunk(
        0,
        0,
    )

    chunk.set_tile(
        0,
        0,
        1,
    )

    tileset = create_tileset()

    cache = TileChunkRenderCache(
        chunk
    )

    cache.get(
        tileset
    )

    assert cache.valid
    assert cache.tile_count == 1

    cache.clear()

    assert not cache.valid
    assert cache.tiles == ()
    assert cache.tile_count == 0


def test_invalid_tile_id_raises():
    chunk = TileChunk(
        0,
        0,
    )

    chunk.set_tile(
        0,
        0,
        999,
    )

    tileset = create_tileset()

    cache = TileChunkRenderCache(
        chunk
    )

    with pytest.raises(
        IndexError
    ):
        cache.get(
            tileset
        )

    assert chunk.dirty
    assert not cache.valid
    assert cache.build_count == 0


def test_cache_iteration():
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
        2,
        3,
        2,
    )

    cache = TileChunkRenderCache(
        chunk
    )

    cache.get(
        create_tileset()
    )

    assert list(
        cache
    ) == list(
        cache.tiles
    )

    assert len(
        cache
    ) == 2


def test_repr():
    chunk = TileChunk(
        2,
        3,
    )

    cache = TileChunkRenderCache(
        chunk
    )

    text = repr(
        cache
    )

    assert "TileChunkRenderCache" in text
    assert "(2, 3)" in text
    assert "build_count=0" in text