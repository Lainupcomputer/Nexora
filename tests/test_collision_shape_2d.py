from __future__ import annotations

import pytest

from nexora.ecs.world import World
from nexora.nodes import (
    Node,
    CollisionShape2D,
)


def create_shape(
    width: float = 32.0,
    height: float = 32.0,
) -> CollisionShape2D:
    return CollisionShape2D(
        "Shape",
        World(),
        width,
        height,
    )


def test_default_size():
    shape = create_shape()

    assert shape.width == pytest.approx(
        32.0
    )

    assert shape.height == pytest.approx(
        32.0
    )


def test_custom_size():
    shape = create_shape(
        16.0,
        24.0,
    )

    assert shape.width == pytest.approx(
        16.0
    )

    assert shape.height == pytest.approx(
        24.0
    )


def test_set_size():
    shape = create_shape()

    shape.set_size(
        20.0,
        40.0,
    )

    assert shape.width == pytest.approx(
        20.0
    )

    assert shape.height == pytest.approx(
        40.0
    )


def test_width_property():
    shape = create_shape()

    shape.width = 64.0

    assert shape.width == pytest.approx(
        64.0
    )


def test_height_property():
    shape = create_shape()

    shape.height = 48.0

    assert shape.height == pytest.approx(
        48.0
    )


def test_invalid_width():
    with pytest.raises(
        ValueError
    ):
        create_shape(
            0.0,
            32.0,
        )


def test_invalid_height():
    with pytest.raises(
        ValueError
    ):
        create_shape(
            32.0,
            0.0,
        )


def test_world_rect_without_parent():
    shape = create_shape(
        16.0,
        24.0,
    )

    shape.transform.x = 10.0
    shape.transform.y = 20.0

    assert shape.world_rect == pytest.approx(
        (
            10.0,
            20.0,
            16.0,
            24.0,
        )
    )


def test_world_rect_uses_parent_position():
    world = World()

    parent = Node(
        "Parent",
        world,
    )

    shape = CollisionShape2D(
        "Shape",
        world,
        16.0,
        24.0,
    )

    parent.transform.x = 100.0
    parent.transform.y = 50.0

    shape.transform.x = 10.0
    shape.transform.y = 20.0

    parent.add_child(
        shape
    )

    assert shape.world_rect == pytest.approx(
        (
            110.0,
            70.0,
            16.0,
            24.0,
        )
    )


def test_world_size_uses_scale():
    shape = create_shape(
        16.0,
        24.0,
    )

    shape.transform.scale_x = 2.0
    shape.transform.scale_y = 3.0

    assert shape.world_size == pytest.approx(
        (
            32.0,
            72.0,
        )
    )


def test_world_size_uses_parent_scale():
    world = World()

    parent = Node(
        "Parent",
        world,
    )

    shape = CollisionShape2D(
        "Shape",
        world,
        16.0,
        24.0,
    )

    parent.transform.scale_x = 2.0
    parent.transform.scale_y = 2.0

    parent.add_child(
        shape
    )

    assert shape.world_size == pytest.approx(
        (
            32.0,
            48.0,
        )
    )


def test_overlap():
    world = World()

    a = CollisionShape2D(
        "A",
        world,
        32.0,
        32.0,
    )

    b = CollisionShape2D(
        "B",
        world,
        32.0,
        32.0,
    )

    a.transform.x = 0.0
    a.transform.y = 0.0

    b.transform.x = 16.0
    b.transform.y = 16.0

    assert a.overlaps(
        b
    )


def test_no_overlap():
    world = World()

    a = CollisionShape2D(
        "A",
        world,
        32.0,
        32.0,
    )

    b = CollisionShape2D(
        "B",
        world,
        32.0,
        32.0,
    )

    b.transform.x = 100.0
    b.transform.y = 100.0

    assert not a.overlaps(
        b
    )


def test_touching_edges_is_not_overlap():
    world = World()

    a = CollisionShape2D(
        "A",
        world,
        32.0,
        32.0,
    )

    b = CollisionShape2D(
        "B",
        world,
        32.0,
        32.0,
    )

    b.transform.x = 32.0

    assert not a.overlaps(
        b
    )


def test_disabled_shape_does_not_overlap():
    world = World()

    a = CollisionShape2D(
        "A",
        world,
    )

    b = CollisionShape2D(
        "B",
        world,
    )

    b.disabled = True

    assert not a.overlaps(
        b
    )


def test_contains_point():
    shape = create_shape(
        32.0,
        32.0,
    )

    shape.transform.x = 100.0
    shape.transform.y = 50.0

    assert shape.contains_point(
        110.0,
        60.0,
    )


def test_does_not_contain_point():
    shape = create_shape(
        32.0,
        32.0,
    )

    assert not shape.contains_point(
        100.0,
        100.0,
    )