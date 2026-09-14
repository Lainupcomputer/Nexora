from __future__ import annotations

from nexora.ecs.world import World
from nexora.nodes import (
    Area2D,
    Body2D,
    CollisionShape2D,
    StaticBody2D,
)


def create_area(
    world: World,
) -> Area2D:
    area = Area2D(
        "Area",
        world,
    )

    shape = CollisionShape2D(
        "Shape",
        world,
        32.0,
        32.0,
    )

    area.add_child(
        shape
    )

    return area


def test_area_is_body():
    area = create_area(
        World()
    )

    assert isinstance(
        area,
        Body2D,
    )


def test_area_defaults():
    area = create_area(
        World()
    )

    assert area.monitoring
    assert area.monitorable


def test_area_overlaps_body():
    world = World()

    area = create_area(
        world
    )

    body = StaticBody2D(
        "Body",
        world,
    )

    shape = CollisionShape2D(
        "Shape",
        world,
        32.0,
        32.0,
    )

    body.add_child(
        shape
    )

    body.transform.x = 16.0

    assert area.overlaps(
        body
    )


def test_area_does_not_overlap_distant_body():
    world = World()

    area = create_area(
        world
    )

    body = StaticBody2D(
        "Body",
        world,
    )

    shape = CollisionShape2D(
        "Shape",
        world,
        32.0,
        32.0,
    )

    body.add_child(
        shape
    )

    body.transform.x = 500.0
    body.transform.y = 500.0

    assert not area.overlaps(
        body
    )


def test_monitoring_false():
    world = World()

    area = create_area(
        world
    )

    body = StaticBody2D(
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

    area.monitoring = False

    assert not area.overlaps(
        body
    )


def test_area_respects_monitorable():
    world = World()

    area_a = create_area(
        world
    )

    area_b = create_area(
        world
    )

    area_b.monitorable = False

    assert not area_a.overlaps(
        area_b
    )


def test_area_child_offset():
    world = World()

    area = Area2D(
        "Interaction",
        world,
    )

    shape = CollisionShape2D(
        "Shape",
        world,
        20.0,
        10.0,
    )

    shape.transform.x = 10.0
    shape.transform.y = 15.0

    area.add_child(
        shape
    )

    area.transform.x = 100.0
    area.transform.y = 50.0

    assert shape.world_rect == (
        110.0,
        65.0,
        20.0,
        10.0,
    )