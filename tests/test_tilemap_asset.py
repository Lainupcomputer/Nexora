from __future__ import annotations

from pathlib import Path

from nexora.ecs.world import World
from nexora.nodes.world.tilemap_node import TileMapNode
from nexora.tilemap import TileMap, TileMapAsset, TileSet


def test_tilemap_asset_roundtrip_preserves_tileset_layout_and_layers(tmp_path: Path) -> None:
    tilemap = TileMap(width=3, height=2, tile_width=64, tile_height=32, projection="angled_2d")
    tilemap.create_layer("ground").set_tile(2, 1, 7)
    tilemap.create_layer("objects", render_layer=20).set_tile(1, 0, 3)
    tileset = TileSet(
        name="World",
        columns=4,
        rows=2,
        tile_width=64,
        tile_height=32,
        spacing_x=2,
        spacing_y=4,
        margin_x=8,
        margin_y=6,
        texture_asset="world/tiles.png",
    )

    path = TileMapAsset.from_components(tilemap, tileset, name="WorldMap").save(
        tmp_path / "world"
    )
    loaded_map, loaded_tileset = TileMapAsset.load(path).build()

    assert path.name == "world.ntmap"
    assert loaded_map.projection.value == "angled_2d"
    assert loaded_map.require_layer("ground").get_tile(2, 1) == 7
    assert loaded_map.require_layer("objects").render_layer == 20
    assert loaded_tileset.texture_asset == "world/tiles.png"
    assert loaded_tileset.pixel_rect(5) == (74, 42, 64, 32)


class _FakeAssets:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[str] = []

    def resolve(self, path: str | Path) -> Path:
        return (self.root / path).resolve()

    def texture(self, path: str, *, force_reload: bool = False):
        del force_reload
        self.calls.append(path)
        return object()


def test_tilemap_node_loads_tilemap_asset_from_assets(tmp_path: Path) -> None:
    assets_root = tmp_path / "assets"
    assets_root.mkdir()
    tilemap = TileMap(width=1, height=1, tile_width=16, tile_height=16)
    tilemap.create_layer("ground").set_tile(0, 0, 2)
    tileset = TileSet(columns=2, rows=1, tile_width=16, tile_height=16, texture_asset="tiles.png")
    asset_path = TileMapAsset.from_components(tilemap, tileset).save(assets_root / "world.ntmap")

    assets = _FakeAssets(assets_root)
    node = TileMapNode("World", World())
    node.load_tilemap_asset("world.ntmap", assets)

    assert node.tilemap_asset == "world.ntmap"
    assert node.tilemap.require_layer("ground").get_tile(0, 0) == 2
    assert assets.calls == ["tiles.png"]


def test_tilemap_asset_preserves_functional_layer_roles() -> None:
    tilemap = TileMap(width=2, height=2, tile_width=32, tile_height=32)
    tilemap.create_layer("Solid", role="collision")
    tilemap.create_layer("Events", role="trigger")
    tileset = TileSet(columns=1, rows=1, tile_width=32, tile_height=32)

    restored_map, _restored_tileset = TileMapAsset.from_components(
        tilemap,
        tileset,
    ).build()

    assert [layer.name for layer in restored_map.layers_with_role("collision")] == ["Solid"]
    assert [layer.name for layer in restored_map.layers_with_role("trigger")] == ["Events"]
