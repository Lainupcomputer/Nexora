from __future__ import annotations

from pathlib import Path

from nexora.ecs.world import World
from nexora.nodes.world.tilemap_node import TileMapNode
from nexora.tilemap import TileMap, TileMetadata, TileSet


class DummyNode:
    def __init__(self, name='spawned'):
        self.name = name
        self.parent = None
        self.transform = type('T', (), {'x': 0.0, 'y': 0.0})()
        self.destroyed = False

    def destroy(self):
        self.destroyed = True
        if self.parent is not None:
            self.parent.remove_child(self)


class FakePrefabSerializer:
    def __init__(self):
        self.calls = []

    def instantiate(self, path, world, *, parent=None, context=None, overrides=None):
        node = DummyNode()
        self.calls.append((Path(path), world, parent, dict(context or {}), dict(overrides or {})))
        if parent is not None:
            # Use a lightweight Node-like child object only for call verification.
            node.parent = parent
        return node


def build_node():
    world = World()
    node = TileMapNode('World', world)
    tilemap = TileMap(
        width=4,
        height=4,
        tile_width=64,
        tile_height=32,
        projection='isometric',
    )
    layer = tilemap.create_layer('objects', render_layer=0, y_sort=True)
    layer.set_tile(1, 2, 3)

    tileset = TileSet(
        columns=4,
        rows=4,
        tile_width=64,
        tile_height=32,
        texture_asset='world/test.png',
    )
    meta = TileMetadata()
    meta.spawn = 'guard.nxprefab'
    meta.teleport = 'beach.nxscene'
    meta.add_tag('interactive')
    tileset.set_metadata(3, meta)

    node.tilemap = tilemap
    node.tileset = tileset
    node.texture = object()
    return node


def test_metadata_at_and_world_query_roundtrip():
    node = build_node()
    hit = node.metadata_at('objects', 1, 2)
    assert hit is not None
    assert hit.tile_id == 3
    assert hit.metadata.teleport == 'beach.nxscene'

    world_x, world_y = node.tile_world_position(1, 2)
    world_hit = node.metadata_at_world('objects', world_x, world_y)
    assert world_hit is not None
    assert (world_hit.tile_x, world_hit.tile_y) == (1, 2)
    assert world_hit.metadata.has_tag('interactive')


def test_iter_metadata_tiles_filters():
    node = build_node()
    hits = list(node.iter_metadata_tiles(tag='interactive'))
    assert len(hits) == 1
    assert hits[0].metadata.spawn == 'guard.nxprefab'


def test_spawn_prefabs_uses_tile_local_position_and_prefab_root(tmp_path):
    node = build_node()
    serializer = FakePrefabSerializer()

    spawned = node.spawn_prefabs(
        serializer,
        prefab_root=tmp_path,
        context={'assets': object()},
    )

    assert len(spawned) == 1
    call = serializer.calls[0]
    assert call[0] == tmp_path / 'guard.nxprefab'
    assert call[2] is node

    expected_x, expected_y = node.tile_local_position(1, 2)
    overrides = call[4]
    assert overrides['transform']['x'] == expected_x
    assert overrides['transform']['y'] == expected_y
