from __future__ import annotations

import pytest

from nexora.tilemap import (
    TileMetadata,
    TileSet,
)


def create_tileset() -> TileSet:
    return TileSet(
        columns=4,
        rows=4,
        tile_width=32,
        tile_height=32,
    )


def test_metadata_defaults():
    metadata = TileMetadata()

    assert metadata.solid is False
    assert metadata.tags == set()
    assert metadata.properties == {}


def test_metadata_can_be_solid():
    metadata = TileMetadata(
        solid=True
    )

    assert metadata.solid


def test_add_tag():
    metadata = TileMetadata()

    metadata.add_tag(
        "wall"
    )

    assert metadata.has_tag(
        "wall"
    )


def test_duplicate_tag_is_safe():
    metadata = TileMetadata()

    metadata.add_tag(
        "wall"
    )

    metadata.add_tag(
        "wall"
    )

    assert metadata.tags == {
        "wall"
    }


def test_empty_tag_rejected():
    metadata = TileMetadata()

    with pytest.raises(
        ValueError
    ):
        metadata.add_tag(
            ""
        )


def test_remove_tag():
    metadata = TileMetadata()

    metadata.add_tag(
        "water"
    )

    assert metadata.remove_tag(
        "water"
    )

    assert not metadata.has_tag(
        "water"
    )


def test_remove_missing_tag_returns_false():
    metadata = TileMetadata()

    assert not metadata.remove_tag(
        "missing"
    )


def test_custom_property():
    metadata = TileMetadata()

    metadata.set_property(
        "damage",
        25,
    )

    assert metadata.get_property(
        "damage"
    ) == 25


def test_property_default():
    metadata = TileMetadata()

    assert metadata.get_property(
        "missing",
        123,
    ) == 123


def test_empty_property_key_rejected():
    metadata = TileMetadata()

    with pytest.raises(
        ValueError
    ):
        metadata.set_property(
            "",
            10,
        )


def test_remove_property():
    metadata = TileMetadata()

    metadata.set_property(
        "speed",
        0.5,
    )

    assert metadata.remove_property(
        "speed"
    )

    assert (
        metadata.get_property(
            "speed"
        )
        is None
    )


def test_tileset_metadata_created_lazily():
    tileset = create_tileset()

    metadata = tileset.metadata(
        3
    )

    assert isinstance(
        metadata,
        TileMetadata,
    )

    assert tileset.get_metadata(
        3
    ) is metadata


def test_tileset_metadata_preserved():
    tileset = create_tileset()

    metadata = tileset.metadata(
        5
    )

    metadata.solid = True

    metadata.add_tag(
        "wall"
    )

    assert tileset.metadata(
        5
    ) is metadata

    assert tileset.is_solid(
        5
    )

    assert tileset.has_tag(
        5,
        "wall",
    )


def test_tile_without_metadata_is_not_solid():
    tileset = create_tileset()

    assert not tileset.is_solid(
        2
    )


def test_tile_without_metadata_has_no_tags():
    tileset = create_tileset()

    assert not tileset.has_tag(
        2,
        "wall",
    )


def test_set_metadata():
    tileset = create_tileset()

    metadata = TileMetadata(
        solid=True
    )

    tileset.set_metadata(
        4,
        metadata,
    )

    assert tileset.get_metadata(
        4
    ) is metadata


def test_set_metadata_rejects_wrong_type():
    tileset = create_tileset()

    with pytest.raises(
        TypeError
    ):
        tileset.set_metadata(
            4,
            object(),
        )


def test_require_metadata():
    tileset = create_tileset()

    metadata = tileset.metadata(
        3
    )

    assert tileset.require_metadata(
        3
    ) is metadata


def test_require_missing_metadata_raises():
    tileset = create_tileset()

    with pytest.raises(
        KeyError
    ):
        tileset.require_metadata(
            3
        )


def test_remove_metadata():
    tileset = create_tileset()

    metadata = tileset.metadata(
        7
    )

    removed = tileset.remove_metadata(
        7
    )

    assert removed is metadata

    assert (
        tileset.get_metadata(
            7
        )
        is None
    )


def test_metadata_invalid_tile_raises():
    tileset = create_tileset()

    with pytest.raises(
        IndexError
    ):
        tileset.metadata(
            999
        )