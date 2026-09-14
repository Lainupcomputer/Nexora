from __future__ import annotations

from nexora.ecs.world import World
from nexora.nodes import (
    Body2D,
    CollisionShape2D,
    StaticBody2D,
)


def test_static_body_is_body():
    body = StaticBody2D(
        "Wall",
        World(),
    )

    assert isinstance(
        body,
        Body2D,
    )


def test_static_body_accepts_collision_shape():
    world = World()

    body = StaticBody2D(
        "Wall",
        world,
    )

    shape = CollisionShape2D(
        "Collision",
        world,
        32.0,
        64.0,
    )

    body.add_child(
        shape
    )

    assert body.primary_collision_shape is shape


def test_static_body_shape_follows_body():
    world = World()

    body = StaticBody2D(
        "Wall",
        world,
    )

    shape = CollisionShape2D(
        "Collision",
        world,
        32.0,
        64.0,
    )

    shape.transform.x = 5.0
    shape.transform.y = 10.0

    body.add_child(
        shape
    )

    body.transform.x = 100.0
    body.transform.y = 50.0

    assert shape.world_rect == (
        105.0,
        60.0,
        32.0,
        64.0,
    )