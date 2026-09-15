from __future__ import annotations

from nexora.ecs.world import World
from nexora.nodes.world.tilemap_node import TileMapNode
from nexora.scene.serialization.registry import NodeFactoryRegistry
from nexora.tilemap import TileMap, TileSet


class FakeAssets:
    def __init__(self):
        self.calls = []

    def texture(self, path, *, force_reload=False):
        self.calls.append((path, force_reload))
        return object()


def test_tilemap_node_registry_roundtrip():
    world = World()
    registry = NodeFactoryRegistry()
    node = TileMapNode("World", world)
    tilemap = TileMap(
        width=4,
        height=4,
        tile_width=64,
        tile_height=32,
        projection="isometric",
    )
    tilemap.create_layer("ground", render_layer=-100).set_tile(0, 0, 1)
    tileset = TileSet(
        columns=4,
        rows=4,
        tile_width=64,
        tile_height=32,
        texture_asset="world/test.png",
    )
    node.tilemap = tilemap
    node.tileset = tileset
    node.texture = object()
    node.base_render_layer = 50

    state = registry.dump_properties(node)
    assets = FakeAssets()
    loaded = registry.create("TileMapNode", "World", world)
    registry.load_properties(loaded, state, context={"assets": assets})

    assert loaded.tilemap is not None
    assert loaded.tileset is not None
    assert loaded.tilemap.projection.value == "isometric"
    assert loaded.base_render_layer == 50
    assert assets.calls == [("world/test.png", False)]
