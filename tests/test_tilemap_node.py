from __future__ import annotations

import pytest

from nexora.ecs.world import World
from nexora.nodes import TileMapNode
from nexora.tilemap import (
    TileMap,
    TileSet,
)


class DummyRenderer:
    def __init__(
        self,
        *,
        width: int = 320,
        height: int = 240,
    ) -> None:
        self.width = width
        self.height = height

        self.calls: list[
            dict
        ] = []

    def sprite(
        self,
        texture,
        x,
        y,
        *,
        width,
        height,
        rotation,
        origin,
        alpha,
        flip_x,
        flip_y,
        uv,
    ) -> None:
        self.calls.append(
            {
                "texture": texture,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "rotation": rotation,
                "origin": origin,
                "alpha": alpha,
                "flip_x": flip_x,
                "flip_y": flip_y,
                "uv": uv,
            }
        )


    def sprites(
        self,
        texture,
        sprites,
        *,
        workers=None,
    ):
        sprites = list(
            sprites
        )

        for sprite in sprites:
            (
                x,
                y,
                width,
                height,
                rotation,
                origin_x,
                origin_y,
                alpha,
                flip_x,
                flip_y,
                uv_x,
                uv_y,
                uv_width,
                uv_height,
            ) = sprite

            self.calls.append(
                {
                    "texture": texture,

                    "x": x,
                    "y": y,

                    "width": width,
                    "height": height,

                    "rotation": rotation,

                    "origin": (
                        origin_x,
                        origin_y,
                    ),

                    "alpha": alpha,

                    "flip_x": flip_x,
                    "flip_y": flip_y,

                    "uv": (
                        uv_x,
                        uv_y,
                        uv_width,
                        uv_height,
                    ),
                }
            )

        return len(
            sprites
        )

def create_node(
    *,
    map_width: int = 10,
    map_height: int = 10,
) -> TileMapNode:
    world = World()

    node = TileMapNode(
        "Map",
        world,
    )

    tilemap = TileMap(
        width=map_width,
        height=map_height,
        tile_width=32,
        tile_height=32,
    )

    tileset = TileSet(
        columns=4,
        rows=4,
        tile_width=32,
        tile_height=32,
    )

    node.set_map(
        tilemap,
        tileset,
        object(),
    )

    return node


def test_tilemap_node_defaults():
    world = World()

    node = TileMapNode(
        "Map",
        world,
    )

    assert node.tilemap is None
    assert node.tileset is None
    assert node.texture is None

    assert node.culling_enabled
    assert node.culling_margin == 1
    assert node.centered

    assert not node.ready


def test_set_map():
    node = create_node()

    assert node.ready

    assert node.tilemap is not None
    assert node.tileset is not None


def test_set_map_rejects_tile_size_mismatch():
    world = World()

    node = TileMapNode(
        "Map",
        world,
    )

    tilemap = TileMap(
        width=10,
        height=10,
        tile_width=32,
        tile_height=32,
    )

    tileset = TileSet(
        columns=4,
        rows=4,
        tile_width=16,
        tile_height=16,
    )

    with pytest.raises(
        ValueError
    ):
        node.set_map(
            tilemap,
            tileset,
            object(),
        )


def test_centered_tile_positions():
    node = create_node(
        map_width=2,
        map_height=2,
    )

    assert node.tile_local_position(
        0,
        0,
    ) == pytest.approx(
        (
            -16.0,
            -16.0,
        )
    )

    assert node.tile_local_position(
        1,
        1,
    ) == pytest.approx(
        (
            16.0,
            16.0,
        )
    )


def test_non_centered_tile_positions():
    node = create_node(
        map_width=2,
        map_height=2,
    )

    node.centered = False

    assert node.tile_local_position(
        0,
        0,
    ) == pytest.approx(
        (
            16.0,
            16.0,
        )
    )


def test_world_position_includes_node_position():
    node = create_node(
        map_width=2,
        map_height=2,
    )

    node.transform.x = 100.0
    node.transform.y = 50.0

    assert node.tile_world_position(
        0,
        0,
    ) == pytest.approx(
        (
            84.0,
            34.0,
        )
    )


def test_render_empty_map_draws_nothing():
    node = create_node()

    renderer = DummyRenderer()

    node.render(
        renderer,
        0.0,
    )

    assert renderer.calls == []
    assert node.last_rendered_tiles == 0


def test_render_one_tile():
    node = create_node(
        map_width=2,
        map_height=2,
    )

    assert node.tilemap is not None

    ground = (
        node.tilemap.create_layer(
            "ground"
        )
    )

    ground.set_tile(
        0,
        0,
        5,
    )

    renderer = DummyRenderer(
        width=320,
        height=240,
    )

    node.render(
        renderer,
        0.0,
    )

    assert len(
        renderer.calls
    ) == 1

    call = renderer.calls[0]

    assert call["uv"] == pytest.approx(
        node.tileset.uv(
            5
        )
    )


def test_hidden_layer_is_not_rendered():
    node = create_node(
        map_width=2,
        map_height=2,
    )

    assert node.tilemap is not None

    layer = node.tilemap.create_layer(
        "ground",
        visible=False,
    )

    layer.set_tile(
        0,
        0,
        1,
    )

    renderer = DummyRenderer()

    node.render(
        renderer,
        0.0,
    )

    assert renderer.calls == []


def test_disabled_layer_is_not_rendered():
    node = create_node(
        map_width=2,
        map_height=2,
    )

    assert node.tilemap is not None

    layer = node.tilemap.create_layer(
        "ground",
        enabled=False,
    )

    layer.set_tile(
        0,
        0,
        1,
    )

    renderer = DummyRenderer()

    node.render(
        renderer,
        0.0,
    )

    assert renderer.calls == []


def test_layer_opacity_is_forwarded():
    node = create_node(
        map_width=2,
        map_height=2,
    )

    assert node.tilemap is not None

    layer = node.tilemap.create_layer(
        "ground",
        opacity=0.4,
    )

    layer.set_tile(
        0,
        0,
        1,
    )

    renderer = DummyRenderer()

    node.render(
        renderer,
        0.0,
    )

    assert renderer.calls[0][
        "alpha"
    ] == pytest.approx(
        0.4
    )


def test_layer_order_is_preserved():
    node = create_node(
        map_width=1,
        map_height=1,
    )

    assert node.tilemap is not None

    ground = node.tilemap.create_layer(
        "ground"
    )

    objects = node.tilemap.create_layer(
        "objects"
    )

    ground.set_tile(
        0,
        0,
        1,
    )

    objects.set_tile(
        0,
        0,
        2,
    )

    renderer = DummyRenderer()

    node.render(
        renderer,
        0.0,
    )

    assert [
        call["uv"]
        for call in renderer.calls
    ] == [
        node.tileset.uv(
            1
        ),
        node.tileset.uv(
            2
        ),
    ]


def test_invalid_tile_id_raises():
    node = create_node(
        map_width=1,
        map_height=1,
    )

    assert node.tilemap is not None

    layer = node.tilemap.create_layer(
        "ground"
    )

    layer.set_tile(
        0,
        0,
        999,
    )

    renderer = DummyRenderer()

    with pytest.raises(
        IndexError
    ):
        node.render(
            renderer,
            0.0,
        )


def test_culling_reduces_visible_area():
    node = create_node(
        map_width=100,
        map_height=100,
    )

    node.culling_margin = 0

    renderer = DummyRenderer(
        width=320,
        height=320,
    )

    (
        min_x,
        min_y,
        max_x,
        max_y,
    ) = node.visible_bounds(
        renderer
    )

    width = (
        max_x
        - min_x
        + 1
    )

    height = (
        max_y
        - min_y
        + 1
    )

    assert width < 100
    assert height < 100


def test_disabled_culling_returns_full_map():
    node = create_node(
        map_width=100,
        map_height=80,
    )

    node.culling_enabled = False

    renderer = DummyRenderer()

    assert node.visible_bounds(
        renderer
    ) == (
        0,
        0,
        99,
        79,
    )


def test_scale_changes_rendered_tile_size():
    node = create_node(
        map_width=1,
        map_height=1,
    )

    node.transform.scale_x = 2.0
    node.transform.scale_y = 3.0

    assert node.tilemap is not None

    layer = node.tilemap.create_layer(
        "ground"
    )

    layer.set_tile(
        0,
        0,
        1,
    )

    renderer = DummyRenderer()

    node.render(
        renderer,
        0.0,
    )

    call = renderer.calls[0]

    assert call["width"] == pytest.approx(
        64.0
    )

    assert call["height"] == pytest.approx(
        96.0
    )

def test_visible_chunk_bounds():
    node = create_node(
        map_width=100,
        map_height=100,
    )

    assert node.tilemap is not None

    layer = (
        node.tilemap.create_layer(
            "ground"
        )
    )

    node.culling_margin = 0

    renderer = DummyRenderer(
        width=320,
        height=320,
    )

    (
        min_chunk_x,
        min_chunk_y,
        max_chunk_x,
        max_chunk_y,
    ) = node.visible_chunk_bounds(
        renderer,
        layer,
    )

    assert min_chunk_x >= 0
    assert min_chunk_y >= 0

    assert (
        max_chunk_x
        < layer.chunk_columns
    )

    assert (
        max_chunk_y
        < layer.chunk_rows
    )


def test_chunk_render_skips_empty_chunks():
    node = create_node(
        map_width=100,
        map_height=100,
    )

    assert node.tilemap is not None

    layer = (
        node.tilemap.create_layer(
            "ground"
        )
    )

    # One tile in the center area.
    layer.set_tile(
        50,
        50,
        3,
    )

    renderer = DummyRenderer(
        width=320,
        height=320,
    )

    node.render(
        renderer,
        0.0,
    )

    assert (
        node.last_visible_chunks
        > 0
    )

    assert (
        node.last_rendered_tiles
        == 1
    )


def test_chunk_render_preserves_tile_uv():
    node = create_node(
        map_width=100,
        map_height=100,
    )

    assert node.tilemap is not None
    assert node.tileset is not None

    layer = (
        node.tilemap.create_layer(
            "ground"
        )
    )

    layer.set_tile(
        50,
        50,
        7,
    )

    renderer = DummyRenderer(
        width=320,
        height=320,
    )

    node.render(
        renderer,
        0.0,
    )

    assert len(
        renderer.calls
    ) == 1

    assert renderer.calls[0][
        "uv"
    ] == pytest.approx(
        node.tileset.uv(
            7
        )
    )


def test_chunk_render_handles_tile_on_chunk_boundary():
    node = create_node(
        map_width=100,
        map_height=100,
    )

    assert node.tilemap is not None

    layer = (
        node.tilemap.create_layer(
            "ground"
        )
    )

    # Boundary between chunk 0 and chunk 1.
    layer.set_tile(
        31,
        50,
        1,
    )

    layer.set_tile(
        32,
        50,
        2,
    )

    # Move map so this region is around screen center.

    node.transform.x = (
        (
            50
            - 31.5
        )
        * 32.0
    )

    renderer = DummyRenderer(
        width=320,
        height=320,
    )

    node.render(
        renderer,
        0.0,
    )

    assert (
        node.last_rendered_tiles
        >= 2
    )