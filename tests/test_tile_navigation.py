from __future__ import annotations

import math

from nexora.tilemap import TileMap, TileMetadata, TileNavigation, TileSet


def make_navigation(*, diagonal=False):
    tilemap = TileMap(
        width=6,
        height=6,
        tile_width=64,
        tile_height=32,
        projection="isometric",
    )
    layer = tilemap.create_layer("ground")
    for y in range(6):
        for x in range(6):
            layer.set_tile(x, y, 0)

    tileset = TileSet(columns=2, rows=1, tile_width=64, tile_height=32)
    tileset.set_metadata(0, TileMetadata(solid=False))
    tileset.set_metadata(1, TileMetadata(solid=True))

    nav = TileNavigation(
        tilemap,
        tileset,
        layer_name="ground",
        allow_diagonal=diagonal,
    )
    return tilemap, layer, tileset, nav


def test_astar_routes_around_solid_tiles():
    _, layer, _, nav = make_navigation()
    for y in range(5):
        layer.set_tile(2, y, 1)
    nav.invalidate()

    path = nav.find_path((0, 0), (5, 0))
    assert path is not None
    assert path.tiles[0] == (0, 0)
    assert path.tiles[-1] == (5, 0)
    assert all(point != (2, y) for y in range(5) for point in path.tiles)


def test_navigation_cost_prefers_cheaper_route():
    _, layer, tileset, nav = make_navigation()
    expensive = TileMetadata(solid=False)
    expensive.navigation_cost = 20.0
    tileset.set_metadata(1, expensive)

    layer.set_tile(1, 0, 1)
    layer.set_tile(2, 0, 1)
    layer.set_tile(3, 0, 1)
    nav.invalidate()

    path = nav.find_path((0, 0), (4, 0))
    assert path is not None
    assert (1, 0) not in path.tiles
    assert path.cost < 60.0


def test_dynamic_blocker_invalidates_cached_path():
    _, _, _, nav = make_navigation()
    first = nav.find_path((0, 0), (3, 0))
    assert first is not None
    assert (1, 0) in first.tiles

    revision = nav.revision
    nav.set_blocked(1, 0)
    assert nav.revision == revision + 1

    second = nav.find_path((0, 0), (3, 0))
    assert second is not None
    assert (1, 0) not in second.tiles


def test_diagonal_navigation_and_corner_cutting_guard():
    _, layer, _, nav = make_navigation(diagonal=True)
    path = nav.find_path((0, 0), (2, 2))
    assert path is not None
    assert math.isclose(path.cost, 2.0 * math.sqrt(2.0), rel_tol=1e-6)

    layer.set_tile(1, 0, 1)
    nav.invalidate()
    blocked_corner = nav.find_path((0, 0), (1, 1))
    assert blocked_corner is not None
    assert blocked_corner.tiles != ((0, 0), (1, 1))


def test_isometric_world_path_uses_projection_conversion():
    tilemap, _, _, nav = make_navigation()
    start_world = tilemap.tile_to_world(0, 0)
    goal_world = tilemap.tile_to_world(4, 3)

    path = nav.find_world_path(*start_world, *goal_world)
    assert path is not None
    assert path.tiles[0] == (0, 0)
    assert path.tiles[-1] == (4, 3)
    assert path.world_points[0] == start_world
    assert path.world_points[-1] == goal_world


def test_empty_tile_policy_is_configurable():
    tilemap = TileMap(width=2, height=1, tile_width=64, tile_height=32)
    tilemap.create_layer("ground")
    tileset = TileSet(columns=1, rows=1, tile_width=64, tile_height=32)

    walkable = TileNavigation(tilemap, tileset, layer_name="ground", empty_walkable=True)
    blocked = TileNavigation(tilemap, tileset, layer_name="ground", empty_walkable=False)

    assert walkable.is_walkable(0, 0)
    assert not blocked.is_walkable(0, 0)
