from __future__ import annotations

import pytest

from nexora.ecs.world import World
from nexora.nodes import (
    Node,
    Body2D,
    CollisionShape2D,
)


def create_body(
    name: str = "Body",
) -> Body2D:
    return Body2D(
        name,
        World(),
    )


def test_defaults():
    body = create_body()

    assert body.collision_layer == 1
    assert body.collision_mask == 0xFFFFFFFF

    assert body.collision_enabled


def test_no_shapes_by_default():
    body = create_body()

    assert body.collision_shapes == ()
    assert body.active_collision_shapes == ()
    assert body.primary_collision_shape is None


def test_collision_shape_child():
    world = World()

    body = Body2D(
        "Body",
        world,
    )

    shape = CollisionShape2D(
        "Shape",
        world,
    )

    body.add_child(
        shape
    )

    assert body.collision_shapes == (
        shape,
    )

    assert body.primary_collision_shape is shape


def test_non_collision_children_are_ignored():
    world = World()

    body = Body2D(
        "Body",
        world,
    )

    child = Node(
        "Child",
        world,
    )

    body.add_child(
        child
    )

    assert body.collision_shapes == ()


def test_multiple_collision_shapes():
    world = World()

    body = Body2D(
        "Body",
        world,
    )

    shape_a = CollisionShape2D(
        "A",
        world,
    )

    shape_b = CollisionShape2D(
        "B",
        world,
    )

    body.add_child(
        shape_a
    )

    body.add_child(
        shape_b
    )

    assert body.collision_shapes == (
        shape_a,
        shape_b,
    )

    assert body.primary_collision_shape is shape_a


def test_disabled_shape_not_active():
    world = World()

    body = Body2D(
        "Body",
        world,
    )

    shape = CollisionShape2D(
        "Shape",
        world,
    )

    body.add_child(
        shape
    )

    shape.disabled = True

    assert body.collision_shapes == (
        shape,
    )

    assert body.active_collision_shapes == ()
    assert body.primary_collision_shape is None


def test_disabled_node_shape_not_active():
    world = World()

    body = Body2D(
        "Body",
        world,
    )

    shape = CollisionShape2D(
        "Shape",
        world,
    )

    body.add_child(
        shape
    )

    shape.enabled = False

    assert body.active_collision_shapes == ()


def test_disabled_body_has_no_active_shapes():
    world = World()

    body = Body2D(
        "Body",
        world,
    )

    shape = CollisionShape2D(
        "Shape",
        world,
    )

    body.add_child(
        shape
    )

    body.collision_enabled = False

    assert body.active_collision_shapes == ()


def test_require_collision_shape():
    world = World()

    body = Body2D(
        "Body",
        world,
    )

    shape = CollisionShape2D(
        "Shape",
        world,
    )

    body.add_child(
        shape
    )

    assert (
        body.require_collision_shape()
        is shape
    )


def test_require_collision_shape_without_shape():
    body = create_body()

    with pytest.raises(
        RuntimeError
    ):
        body.require_collision_shape()


def test_layer_helpers():
    body = create_body()

    body.set_collision_layer(
        0
    )

    body.add_collision_layer(
        1
    )

    body.add_collision_layer(
        3
    )

    assert body.has_collision_layer(
        1
    )

    assert not body.has_collision_layer(
        2
    )

    assert body.has_collision_layer(
        3
    )

    body.remove_collision_layer(
        1
    )

    assert not body.has_collision_layer(
        1
    )


def test_mask_helpers():
    body = create_body()

    body.set_collision_mask(
        0
    )

    body.add_collision_mask(
        2
    )

    body.add_collision_mask(
        4
    )

    assert body.has_collision_mask(
        2
    )

    assert body.has_collision_mask(
        4
    )

    assert not body.has_collision_mask(
        1
    )

    body.remove_collision_mask(
        2
    )

    assert not body.has_collision_mask(
        2
    )


def test_can_detect():
    world = World()

    a = Body2D(
        "A",
        world,
    )

    b = Body2D(
        "B",
        world,
    )

    a.set_collision_mask(
        0
    )

    b.set_collision_layer(
        1
    )

    assert not a.can_detect(
        b
    )

    a.add_collision_mask(
        1
    )

    assert a.can_detect(
        b
    )


def test_can_collide_with():
    world = World()

    a = Body2D(
        "A",
        world,
    )

    b = Body2D(
        "B",
        world,
    )

    a.set_collision_layer(
        1
    )

    a.set_collision_mask(
        2
    )

    b.set_collision_layer(
        2
    )

    b.set_collision_mask(
        1
    )

    assert a.can_collide_with(
        b
    )

    assert b.can_collide_with(
        a
    )


def test_collision_requires_both_masks():
    world = World()

    a = Body2D(
        "A",
        world,
    )

    b = Body2D(
        "B",
        world,
    )

    a.set_collision_layer(
        1
    )

    a.set_collision_mask(
        2
    )

    b.set_collision_layer(
        2
    )

    b.set_collision_mask(
        0
    )

    assert a.can_detect(
        b
    )

    assert not a.can_collide_with(
        b
    )


def test_overlaps_body():
    world = World()

    a = Body2D(
        "A",
        world,
    )

    b = Body2D(
        "B",
        world,
    )

    shape_a = CollisionShape2D(
        "ShapeA",
        world,
        32.0,
        32.0,
    )

    shape_b = CollisionShape2D(
        "ShapeB",
        world,
        32.0,
        32.0,
    )

    a.add_child(
        shape_a
    )

    b.add_child(
        shape_b
    )

    b.transform.x = 16.0

    assert a.overlaps_body(
        b
    )


def test_multiple_shapes_overlap():
    world = World()

    a = Body2D(
        "A",
        world,
    )

    b = Body2D(
        "B",
        world,
    )

    a_left = CollisionShape2D(
        "Left",
        world,
        16.0,
        16.0,
    )

    a_right = CollisionShape2D(
        "Right",
        world,
        16.0,
        16.0,
    )

    a_right.transform.x = 100.0

    target = CollisionShape2D(
        "Target",
        world,
        16.0,
        16.0,
    )

    b.transform.x = 100.0

    a.add_child(
        a_left
    )

    a.add_child(
        a_right
    )

    b.add_child(
        target
    )

    assert a.overlaps_body(
        b
    )


def test_set_world_position_without_parent():
    body = create_body()

    body.set_world_position(
        100.0,
        50.0,
    )

    assert body.world_position == pytest.approx(
        (
            100.0,
            50.0,
        )
    )


def test_set_world_position_with_parent():
    world = World()

    parent = Node(
        "Parent",
        world,
    )

    body = Body2D(
        "Body",
        world,
    )

    parent.transform.x = 100.0
    parent.transform.y = 50.0

    parent.add_child(
        body
    )

    body.set_world_position(
        150.0,
        80.0,
    )

    assert body.world_position == pytest.approx(
        (
            150.0,
            80.0,
        )
    )


def test_set_world_position_with_scaled_parent():
    world = World()

    parent = Node(
        "Parent",
        world,
    )

    body = Body2D(
        "Body",
        world,
    )

    parent.transform.x = 100.0
    parent.transform.y = 50.0

    parent.transform.scale_x = 2.0
    parent.transform.scale_y = 3.0

    parent.add_child(
        body
    )

    body.set_world_position(
        140.0,
        110.0,
    )

    assert body.world_position == pytest.approx(
        (
            140.0,
            110.0,
        )
    )


def test_translate_world():
    body = create_body()

    body.transform.x = 10.0
    body.transform.y = 20.0

    body.translate_world(
        5.0,
        -10.0,
    )

    assert body.world_position == pytest.approx(
        (
            15.0,
            10.0,
        )
    )