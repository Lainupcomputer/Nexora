from __future__ import annotations

import pytest

from nexora.editor import TileMapEditorModel
from nexora.editor.commands import CommandStack
from nexora.ecs.world import World
from nexora.nodes.world.tilemap_node import TileMapNode
from nexora.tilemap import TileMap, TileProjection, TileSet


def make_node(*, projection=TileProjection.ORTHOGONAL):
    tilemap = TileMap(
        name="EditorMap",
        width=4,
        height=3,
        tile_width=32,
        tile_height=32,
        projection=projection,
    )
    tilemap.create_layer("ground")
    tileset = TileSet(
        columns=4,
        rows=4,
        tile_width=32,
        tile_height=32,
    )
    node = TileMapNode("Map", World())
    node.set_map(tilemap, tileset, texture=None)
    return node


def test_paint_and_erase_are_single_undoable_operations():
    model = TileMapEditorModel(make_node())
    stack = CommandStack()

    stack.execute(model.paint_command([(0, 0), (1, 0), (1, 0)], tile_id=3))
    layer = model.active_layer
    assert layer.get_tile(0, 0) == 3
    assert layer.get_tile(1, 0) == 3
    assert stack.undo_label == "Paint Tiles"

    stack.undo()
    assert layer.is_empty(0, 0)
    assert layer.is_empty(1, 0)
    stack.redo()
    assert layer.get_tile(1, 0) == 3

    stack.execute(model.erase_command([(0, 0), (1, 0)]))
    assert layer.is_empty(0, 0)
    assert layer.is_empty(1, 0)
    stack.undo()
    assert layer.get_tile(0, 0) == 3
    assert layer.get_tile(1, 0) == 3


def test_fill_records_previous_values_for_undo():
    model = TileMapEditorModel(make_node())
    layer = model.active_layer
    layer.set_tile(0, 0, 1)
    layer.set_tile(2, 2, 2)
    stack = CommandStack()

    stack.execute(model.fill_command(tile_id=5))
    assert all(
        layer.get_tile(x, y) == 5
        for y in range(3)
        for x in range(4)
    )

    stack.undo()
    assert layer.get_tile(0, 0) == 1
    assert layer.get_tile(2, 2) == 2
    assert layer.is_empty(1, 1)


def test_world_cell_conversion_supports_centered_orthogonal_map():
    model = TileMapEditorModel(make_node())
    center = model.world_position_for_cell(2, 1)

    assert model.cell_from_world(*center) == (2, 1)
    assert model.cell_from_world(-1000, -1000) is None


def test_world_cell_conversion_supports_isometric_map():
    model = TileMapEditorModel(
        make_node(projection=TileProjection.ISOMETRIC)
    )

    for cell in ((0, 0), (1, 0), (0, 1), (3, 2)):
        assert model.cell_from_world(
            *model.world_position_for_cell(*cell)
        ) == cell


def test_model_validates_active_layer_and_tile_ids():
    model = TileMapEditorModel(make_node())

    with pytest.raises(ValueError):
        model.paint_command([(0, 0)])

    with pytest.raises(IndexError):
        model.set_selected_tile(99)

    model.set_selected_tile(2)
    assert model.paint_command([(0, 0)]).edits[0].after == 2

    with pytest.raises(KeyError):
        model.set_active_layer("missing")
