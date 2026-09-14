from __future__ import annotations

import pytest

from nexora.ecs.world import World

from nexora.nodes import (
    Area2D,
    CharacterBody2D,
    CollisionShape2D,
    Node,
    RayCast2D,
    StaticBody2D,
)


def create_wall(
    world: World,
    x: float,
    y: float,
    *,
    width: float = 32.0,
    height: float = 32.0,
) -> StaticBody2D:
    wall = StaticBody2D(
        "Wall",
        world,
    )

    wall.transform.x = x
    wall.transform.y = y

    shape = CollisionShape2D(
        "Collision",
        world,
        width,
        height,
    )

    wall.add_child(
        shape
    )

    return wall


def create_ray(
    world: World,
    *,
    target_x: float = 100.0,
    target_y: float = 0.0,
) -> RayCast2D:
    return RayCast2D(
        "Ray",
        world,
        target_x=target_x,
        target_y=target_y,
    )


def test_no_hit():
    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = create_ray(
        world
    )

    root.add_child(
        ray
    )

    hit = ray.force_raycast_update()

    assert hit is None
    assert not ray.is_colliding


def test_hits_static_body():
    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = create_ray(
        world
    )

    wall = create_wall(
        world,
        50.0,
        -16.0,
    )

    root.add_child(
        ray
    )

    root.add_child(
        wall
    )

    hit = ray.force_raycast_update()

    assert hit is not None
    assert hit.collider is wall

    assert ray.is_colliding
    assert ray.get_collider() is wall


def test_returns_nearest_body():
    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = create_ray(
        world,
        target_x=200.0,
    )

    near = create_wall(
        world,
        50.0,
        -16.0,
    )

    far = create_wall(
        world,
        120.0,
        -16.0,
    )

    root.add_child(
        ray
    )

    root.add_child(
        far
    )

    root.add_child(
        near
    )

    hit = ray.force_raycast_update()

    assert hit is not None
    assert hit.collider is near


def test_collision_point():
    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = create_ray(
        world
    )

    wall = create_wall(
        world,
        50.0,
        -16.0,
    )

    root.add_child(
        ray
    )

    root.add_child(
        wall
    )

    hit = ray.force_raycast_update()

    assert hit is not None

    assert hit.point == pytest.approx(
        (
            50.0,
            0.0,
        )
    )


def test_collision_normal():
    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = create_ray(
        world
    )

    wall = create_wall(
        world,
        50.0,
        -16.0,
    )

    root.add_child(
        ray
    )

    root.add_child(
        wall
    )

    hit = ray.force_raycast_update()

    assert hit is not None

    assert hit.normal == pytest.approx(
        (
            -1.0,
            0.0,
        )
    )


def test_collision_distance():
    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = create_ray(
        world,
        target_x=100.0,
    )

    wall = create_wall(
        world,
        50.0,
        -16.0,
    )

    root.add_child(
        ray
    )

    root.add_child(
        wall
    )

    hit = ray.force_raycast_update()

    assert hit is not None

    assert hit.distance == pytest.approx(
        50.0
    )

    assert hit.fraction == pytest.approx(
        0.5
    )


def test_ray_misses_body_outside_segment():
    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = create_ray(
        world,
        target_x=100.0,
    )

    wall = create_wall(
        world,
        150.0,
        -16.0,
    )

    root.add_child(
        ray
    )

    root.add_child(
        wall
    )

    assert (
        ray.force_raycast_update()
        is None
    )


def test_vertical_ray():
    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = create_ray(
        world,
        target_x=0.0,
        target_y=100.0,
    )

    wall = create_wall(
        world,
        -16.0,
        50.0,
    )

    root.add_child(
        ray
    )

    root.add_child(
        wall
    )

    hit = ray.force_raycast_update()

    assert hit is not None

    assert hit.point == pytest.approx(
        (
            0.0,
            50.0,
        )
    )

    assert hit.normal == pytest.approx(
        (
            0.0,
            -1.0,
        )
    )


def test_parent_body_is_ignored():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = CharacterBody2D(
        "Player",
        world,
    )

    player_shape = CollisionShape2D(
        "Collision",
        world,
        32.0,
        32.0,
    )

    player.add_child(
        player_shape
    )

    ray = create_ray(
        world
    )

    player.add_child(
        ray
    )

    root.add_child(
        player
    )

    wall = create_wall(
        world,
        50.0,
        0.0,
    )

    root.add_child(
        wall
    )

    hit = ray.force_raycast_update()

    assert hit is not None
    assert hit.collider is wall


def test_exception_is_ignored():
    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = create_ray(
        world,
        target_x=200.0,
    )

    first = create_wall(
        world,
        50.0,
        -16.0,
    )

    second = create_wall(
        world,
        100.0,
        -16.0,
    )

    root.add_child(
        ray
    )

    root.add_child(
        first
    )

    root.add_child(
        second
    )

    ray.add_exception(
        first
    )

    hit = ray.force_raycast_update()

    assert hit is not None
    assert hit.collider is second


def test_collision_mask():
    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = create_ray(
        world
    )

    wall = create_wall(
        world,
        50.0,
        -16.0,
    )

    wall.set_collision_layer(
        2
    )

    ray.set_collision_mask(
        0
    )

    ray.add_collision_mask(
        2
    )

    root.add_child(
        ray
    )

    root.add_child(
        wall
    )

    hit = ray.force_raycast_update()

    assert hit is not None
    assert hit.collider is wall


def test_wrong_collision_mask_does_not_hit():
    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = create_ray(
        world
    )

    wall = create_wall(
        world,
        50.0,
        -16.0,
    )

    wall.set_collision_layer(
        2
    )

    ray.set_collision_mask(
        1
    )

    root.add_child(
        ray
    )

    root.add_child(
        wall
    )

    assert (
        ray.force_raycast_update()
        is None
    )


def test_hits_area():
    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = create_ray(
        world
    )

    area = Area2D(
        "Area",
        world,
    )

    area.transform.x = 50.0
    area.transform.y = -16.0

    shape = CollisionShape2D(
        "Collision",
        world,
        32.0,
        32.0,
    )

    area.add_child(
        shape
    )

    root.add_child(
        ray
    )

    root.add_child(
        area
    )

    hit = ray.force_raycast_update()

    assert hit is not None
    assert hit.collider is area


def test_can_ignore_areas():
    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = create_ray(
        world
    )

    ray.collide_with_areas = False

    area = Area2D(
        "Area",
        world,
    )

    area.transform.x = 50.0
    area.transform.y = -16.0

    shape = CollisionShape2D(
        "Collision",
        world,
        32.0,
        32.0,
    )

    area.add_child(
        shape
    )

    root.add_child(
        ray
    )

    root.add_child(
        area
    )

    assert (
        ray.force_raycast_update()
        is None
    )


def test_disabled_raycast():
    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = create_ray(
        world
    )

    wall = create_wall(
        world,
        50.0,
        -16.0,
    )

    root.add_child(
        ray
    )

    root.add_child(
        wall
    )

    ray.raycast_enabled = False

    assert (
        ray.force_raycast_update()
        is None
    )

    assert not ray.is_colliding


def test_rotation_affects_ray():
    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = create_ray(
        world,
        target_x=100.0,
        target_y=0.0,
    )

    ray.transform.rotation = 90.0

    wall = create_wall(
        world,
        -16.0,
        50.0,
    )

    root.add_child(
        ray
    )

    root.add_child(
        wall
    )

    hit = ray.force_raycast_update()

    assert hit is not None
    assert hit.collider is wall