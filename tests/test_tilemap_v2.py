from __future__ import annotations

import math

from nexora.tilemap import (
    TileAnimation,
    TileAnimationFrame,
    TileMap,
    TileMetadata,
    TileProjection,
    TileSet,
)


def test_isometric_projection_roundtrip():
    tilemap = TileMap(
        name="Iso",
        width=20,
        height=20,
        tile_width=64,
        tile_height=32,
        projection=TileProjection.ISOMETRIC,
    )

    for x, y in [(0, 0), (1, 0), (0, 1), (5, 7), (19, 19)]:
        world_x, world_y = tilemap.tile_to_world(x, y)
        assert tilemap.world_to_tile(world_x, world_y) == (x, y)


def test_isometric_pixel_size():
    tilemap = TileMap(
        width=10,
        height=6,
        tile_width=64,
        tile_height=32,
        projection="isometric",
    )
    assert tilemap.pixel_width == 512
    assert tilemap.pixel_height == 256


def test_isometric_layers_default_to_y_sort():
    tilemap = TileMap(
        width=8,
        height=8,
        tile_width=64,
        tile_height=32,
        projection="isometric",
    )
    layer = tilemap.create_layer("objects", render_layer=100)
    assert layer.y_sort is True
    assert layer.render_layer == 100


def test_tilemap_state_roundtrip_preserves_projection_layers_and_tiles():
    tilemap = TileMap(
        name="HQ",
        width=4,
        height=3,
        tile_width=64,
        tile_height=32,
        projection="isometric",
    )
    ground = tilemap.create_layer("ground", render_layer=-100, y_sort=False)
    objects = tilemap.create_layer("objects", render_layer=0, y_sort=True)
    ground.set_tile(1, 2, 3)
    objects.set_tile(2, 1, 5)

    restored = TileMap.from_state(tilemap.to_state())

    assert restored.name == "HQ"
    assert restored.projection is TileProjection.ISOMETRIC
    assert restored.require_layer("ground").get_tile(1, 2) == 3
    assert restored.require_layer("objects").get_tile(2, 1) == 5
    assert restored.require_layer("ground").render_layer == -100
    assert restored.require_layer("objects").y_sort is True


def test_tileset_asset_metadata_animation_state_roundtrip():
    tileset = TileSet(
        name="HQ",
        columns=4,
        rows=4,
        tile_width=64,
        tile_height=32,
        texture_asset="world/hq_tiles.png",
    )
    meta = TileMetadata(solid=True)
    meta.damage = 12.5
    meta.teleport = "beach.nxscene"
    meta.spawn = "prefabs/guard.nxprefab"
    meta.add_tag("hazard")
    tileset.set_metadata(2, meta)
    tileset.set_animation(
        3,
        TileAnimation([
            TileAnimationFrame(3, 0.1),
            TileAnimationFrame(4, 0.2),
        ]),
    )

    restored = TileSet.from_state(tileset.to_state())

    assert restored.texture_asset == "world/hq_tiles.png"
    restored_meta = restored.require_metadata(2)
    assert restored_meta.solid is True
    assert restored_meta.damage == 12.5
    assert restored_meta.teleport == "beach.nxscene"
    assert restored_meta.spawn == "prefabs/guard.nxprefab"
    assert restored_meta.has_tag("hazard")
    assert restored.resolve_tile(3, 0.05) == 3
    assert restored.resolve_tile(3, 0.15) == 4
