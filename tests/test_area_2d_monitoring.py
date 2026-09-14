from __future__ import annotations

from nexora.ecs.world import World

from nexora.nodes import (
    Area2D,
    CharacterBody2D,
    CollisionShape2D,
    Node,
    StaticBody2D,
)


def create_area(
    world: World,
    name: str = "Area",
) -> Area2D:
    area = Area2D(
        name,
        world,
    )

    shape = CollisionShape2D(
        "Collision",
        world,
        32.0,
        32.0,
    )

    area.add_child(
        shape
    )

    return area


def create_body(
    world: World,
    name: str = "Body",
) -> StaticBody2D:
    body = StaticBody2D(
        name,
        world,
    )

    shape = CollisionShape2D(
        "Collision",
        world,
        16.0,
        16.0,
    )

    body.add_child(
        shape
    )

    return body


def test_area_detects_body():
    world = World()

    root = Node(
        "Root",
        world,
    )

    area = create_area(
        world
    )

    body = create_body(
        world
    )

    root.add_child(
        area
    )

    root.add_child(
        body
    )

    body.transform.x = 8.0
    body.transform.y = 8.0

    area.update_overlaps()

    assert body in area.overlapping_bodies


def test_area_body_entered():
    world = World()

    root = Node(
        "Root",
        world,
    )

    area = create_area(
        world
    )

    body = create_body(
        world
    )

    root.add_child(
        area
    )

    root.add_child(
        body
    )

    events = []

    area.connect_body_entered(
        events.append
    )

    body.transform.x = 100.0

    area.update_overlaps()

    assert events == []

    body.transform.x = 10.0

    area.update_overlaps()

    assert events == [
        body
    ]


def test_area_body_entered_only_once():
    world = World()

    root = Node(
        "Root",
        world,
    )

    area = create_area(
        world
    )

    body = create_body(
        world
    )

    root.add_child(
        area
    )

    root.add_child(
        body
    )

    events = []

    area.connect_body_entered(
        events.append
    )

    area.update_overlaps()
    area.update_overlaps()
    area.update_overlaps()

    assert events == [
        body
    ]


def test_area_body_exited():
    world = World()

    root = Node(
        "Root",
        world,
    )

    area = create_area(
        world
    )

    body = create_body(
        world
    )

    root.add_child(
        area
    )

    root.add_child(
        body
    )

    events = []

    area.connect_body_exited(
        events.append
    )

    area.update_overlaps()

    assert body in area.overlapping_bodies

    body.transform.x = 100.0

    area.update_overlaps()

    assert events == [
        body
    ]

    assert body not in area.overlapping_bodies


def test_monitoring_false():
    world = World()

    root = Node(
        "Root",
        world,
    )

    area = create_area(
        world
    )

    body = create_body(
        world
    )

    root.add_child(
        area
    )

    root.add_child(
        body
    )

    area.monitoring = False

    area.update_overlaps()

    assert area.overlapping_bodies == ()


def test_disabling_monitoring_emits_exit():
    world = World()

    root = Node(
        "Root",
        world,
    )

    area = create_area(
        world
    )

    body = create_body(
        world
    )

    root.add_child(
        area
    )

    root.add_child(
        body
    )

    exited = []

    area.connect_body_exited(
        exited.append
    )

    area.update_overlaps()

    area.monitoring = False

    area.update_overlaps()

    assert exited == [
        body
    ]


def test_collision_mask_is_respected():
    world = World()

    root = Node(
        "Root",
        world,
    )

    area = create_area(
        world
    )

    body = create_body(
        world
    )

    root.add_child(
        area
    )

    root.add_child(
        body
    )

    area.set_collision_mask(
        0
    )

    area.update_overlaps()

    assert body not in area.overlapping_bodies


def test_area_detects_character():
    world = World()

    root = Node(
        "Root",
        world,
    )

    area = create_area(
        world
    )

    player = CharacterBody2D(
        "Player",
        world,
    )

    player_shape = CollisionShape2D(
        "Collision",
        world,
        16.0,
        16.0,
    )

    player.add_child(
        player_shape
    )

    root.add_child(
        area
    )

    root.add_child(
        player
    )

    area.update_overlaps()

    assert player in area.overlapping_bodies


def test_area_detects_monitorable_area():
    world = World()

    root = Node(
        "Root",
        world,
    )

    area_a = create_area(
        world,
        "AreaA",
    )

    area_b = create_area(
        world,
        "AreaB",
    )

    root.add_child(
        area_a
    )

    root.add_child(
        area_b
    )

    area_a.update_overlaps()

    assert area_b in area_a.overlapping_bodies


def test_non_monitorable_area_is_ignored():
    world = World()

    root = Node(
        "Root",
        world,
    )

    area_a = create_area(
        world,
        "AreaA",
    )

    area_b = create_area(
        world,
        "AreaB",
    )

    area_b.monitorable = False

    root.add_child(
        area_a
    )

    root.add_child(
        area_b
    )

    area_a.update_overlaps()

    assert area_b not in area_a.overlapping_bodies


def test_overlaps_body_now():
    world = World()

    root = Node(
        "Root",
        world,
    )

    area = create_area(
        world
    )

    body = create_body(
        world
    )

    root.add_child(
        area
    )

    root.add_child(
        body
    )

    assert area.overlaps_body_now(
        body
    )


def test_clear_overlaps():
    world = World()

    root = Node(
        "Root",
        world,
    )

    area = create_area(
        world
    )

    body = create_body(
        world
    )

    root.add_child(
        area
    )

    root.add_child(
        body
    )

    area.update_overlaps()

    assert body in area.overlapping_bodies

    area.clear_overlaps()

    assert area.overlapping_bodies == ()