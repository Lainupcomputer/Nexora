from __future__ import annotations

from nexora.ecs.world import World

from nexora.nodes import (
    CollisionShape2D,
    StaticBody2D,
)

from nexora.physics import (
    PhysicsWorld2D,
    get_physics_world,
)


def create_body(
    world: World,
    name: str,
    x: float,
    y: float,
) -> StaticBody2D:
    body = StaticBody2D(
        name,
        world,
    )

    body.transform.x = x
    body.transform.y = y

    shape = CollisionShape2D(
        "Collision",
        world,
        32.0,
        32.0,
    )

    body.add_child(
        shape
    )

    return body


def test_same_world_returns_same_physics_world():
    world = World()

    physics_a = get_physics_world(
        world
    )

    physics_b = get_physics_world(
        world
    )

    assert physics_a is physics_b


def test_different_worlds_have_different_physics_worlds():
    world_a = World()
    world_b = World()

    physics_a = get_physics_world(
        world_a
    )

    physics_b = get_physics_world(
        world_b
    )

    assert physics_a is not physics_b


def test_custom_cell_size():
    world = World()

    physics = PhysicsWorld2D(
        world,
        cell_size=64.0,
    )

    assert physics.cell_size == 64.0


def test_invalid_cell_size():
    world = World()

    try:
        PhysicsWorld2D(
            world,
            cell_size=0.0,
        )

    except ValueError:
        pass

    else:
        raise AssertionError(
            "Expected ValueError for cell_size <= 0."
        )


def test_body_registers_automatically():
    world = World()

    body = create_body(
        world,
        "Body",
        0.0,
        0.0,
    )

    physics = get_physics_world(
        world
    )

    assert body in physics.bodies
    assert physics.body_count == 1


def test_multiple_bodies_register():
    world = World()

    body_a = create_body(
        world,
        "A",
        0.0,
        0.0,
    )

    body_b = create_body(
        world,
        "B",
        100.0,
        100.0,
    )

    physics = get_physics_world(
        world
    )

    assert body_a in physics.bodies
    assert body_b in physics.bodies

    assert physics.body_count == 2


def test_rebuild_populates_grid():
    world = World()

    create_body(
        world,
        "Body",
        0.0,
        0.0,
    )

    physics = get_physics_world(
        world
    )

    physics.rebuild()

    assert physics.cell_count > 0


def test_query_finds_nearby_body():
    world = World()

    body = create_body(
        world,
        "Body",
        50.0,
        50.0,
    )

    physics = get_physics_world(
        world
    )

    physics.rebuild()

    result = physics.query_aabb(
        40.0,
        40.0,
        64.0,
        64.0,
    )

    assert body in result


def test_query_does_not_find_distant_body():
    world = World()

    body = create_body(
        world,
        "Body",
        1000.0,
        1000.0,
    )

    physics = get_physics_world(
        world
    )

    physics.rebuild()

    result = physics.query_aabb(
        0.0,
        0.0,
        64.0,
        64.0,
    )

    assert body not in result


def test_query_excludes_body():
    world = World()

    body = create_body(
        world,
        "Body",
        0.0,
        0.0,
    )

    physics = get_physics_world(
        world
    )

    physics.rebuild()

    result = physics.query_aabb(
        0.0,
        0.0,
        64.0,
        64.0,
        exclude=body,
    )

    assert body not in result


def test_body_without_shape_is_not_inserted():
    world = World()

    body = StaticBody2D(
        "Body",
        world,
    )

    physics = get_physics_world(
        world
    )

    physics.rebuild()

    result = physics.query_aabb(
        0.0,
        0.0,
        64.0,
        64.0,
    )

    assert body not in result


def test_disabled_body_is_not_inserted():
    world = World()

    body = create_body(
        world,
        "Body",
        0.0,
        0.0,
    )

    body.collision_enabled = False

    physics = get_physics_world(
        world
    )

    physics.rebuild()

    result = physics.query_aabb(
        0.0,
        0.0,
        64.0,
        64.0,
    )

    assert body not in result


def test_disabled_node_is_not_inserted():
    world = World()

    body = create_body(
        world,
        "Body",
        0.0,
        0.0,
    )

    body.enabled = False

    physics = get_physics_world(
        world
    )

    physics.rebuild()

    result = physics.query_aabb(
        0.0,
        0.0,
        64.0,
        64.0,
    )

    assert body not in result


def test_update_body_moves_spatial_proxy():
    world = World()

    body = create_body(
        world,
        "Body",
        0.0,
        0.0,
    )

    physics = get_physics_world(
        world
    )

    physics.rebuild()

    assert body in physics.query_aabb(
        0.0,
        0.0,
        64.0,
        64.0,
    )

    body.set_world_position(
        1000.0,
        1000.0,
    )

    assert body not in physics.query_aabb(
        0.0,
        0.0,
        64.0,
        64.0,
    )

    assert body in physics.query_aabb(
        950.0,
        950.0,
        128.0,
        128.0,
    )


def test_sync_physics_updates_proxy():
    world = World()

    body = create_body(
        world,
        "Body",
        0.0,
        0.0,
    )

    physics = get_physics_world(
        world
    )

    physics.rebuild()

    body.transform.x = 500.0
    body.transform.y = 500.0

    # Direct transform changes do not automatically know that
    # broadphase must be updated until sync_physics() is called.
    body.sync_physics()

    assert body not in physics.query_aabb(
        0.0,
        0.0,
        64.0,
        64.0,
    )

    assert body in physics.query_aabb(
        480.0,
        480.0,
        96.0,
        96.0,
    )


def test_destroy_unregisters_body():
    world = World()

    body = create_body(
        world,
        "Body",
        0.0,
        0.0,
    )

    physics = get_physics_world(
        world
    )

    assert body in physics.bodies

    body.destroy()

    assert body not in physics.bodies


def test_large_body_occupies_multiple_cells():
    world = World()

    body = StaticBody2D(
        "LargeBody",
        world,
    )

    shape = CollisionShape2D(
        "Collision",
        world,
        400.0,
        400.0,
    )

    body.add_child(
        shape
    )

    physics = get_physics_world(
        world
    )

    physics.rebuild()

    assert physics.cell_count > 1


def test_query_large_body_from_different_cells():
    world = World()

    body = StaticBody2D(
        "LargeBody",
        world,
    )

    shape = CollisionShape2D(
        "Collision",
        world,
        400.0,
        400.0,
    )

    body.add_child(
        shape
    )

    physics = get_physics_world(
        world
    )

    physics.rebuild()

    result_top_left = physics.query_aabb(
        0.0,
        0.0,
        32.0,
        32.0,
    )

    result_bottom_right = physics.query_aabb(
        350.0,
        350.0,
        32.0,
        32.0,
    )

    assert body in result_top_left
    assert body in result_bottom_right


def test_multiple_collision_shapes_expand_aabb():
    world = World()

    body = StaticBody2D(
        "Body",
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

    shape_b.transform.x = 200.0

    body.add_child(
        shape_a
    )

    body.add_child(
        shape_b
    )

    aabb = body.collision_aabb

    assert aabb is not None

    x, y, width, height = aabb

    assert x == 0.0
    assert y == 0.0

    assert width == 232.0
    assert height == 32.0


def test_query_multiple_shapes():
    world = World()

    body = StaticBody2D(
        "Body",
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

    shape_b.transform.x = 200.0

    body.add_child(
        shape_a
    )

    body.add_child(
        shape_b
    )

    physics = get_physics_world(
        world
    )

    physics.rebuild()

    result = physics.query_aabb(
        190.0,
        0.0,
        64.0,
        64.0,
    )

    assert body in result


def test_mark_dirty_rebuilds_on_query():
    world = World()

    body = create_body(
        world,
        "Body",
        0.0,
        0.0,
    )

    physics = get_physics_world(
        world
    )

    physics.rebuild()

    body.transform.x = 500.0

    physics.mark_dirty()

    result = physics.query_aabb(
        480.0,
        0.0,
        96.0,
        64.0,
    )

    assert body in result


def test_query_returns_unique_body():
    world = World()

    body = StaticBody2D(
        "LargeBody",
        world,
    )

    shape = CollisionShape2D(
        "Collision",
        world,
        400.0,
        400.0,
    )

    body.add_child(
        shape
    )

    physics = get_physics_world(
        world
    )

    physics.rebuild()

    result = physics.query_aabb(
        0.0,
        0.0,
        400.0,
        400.0,
    )

    assert result.count(
        body
    ) == 1