from __future__ import annotations

from nexora.debug.physics import (
    PhysicsDebugRenderer,
)

from nexora.ecs.world import World

from nexora.nodes import (
    Area2D,
    CharacterBody2D,
    CollisionShape2D,
    Node,
    StaticBody2D,
)


class FakeRenderer:
    def __init__(
        self,
    ) -> None:
        self.lines = []

    def line(
        self,
        x1,
        y1,
        x2,
        y2,
        *,
        width=1.0,
        color=(
            1.0,
            1.0,
            1.0,
            1.0,
        ),
    ):
        self.lines.append(
            (
                x1,
                y1,
                x2,
                y2,
                width,
                color,
            )
        )


def create_character(
    world: World,
) -> CharacterBody2D:
    body = CharacterBody2D(
        "Player",
        world,
    )

    shape = CollisionShape2D(
        "Collision",
        world,
        16.0,
        24.0,
    )

    body.add_child(
        shape
    )

    return body


def test_hidden_debug_draws_nothing():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    root.add_child(
        player
    )

    renderer = FakeRenderer()

    debug = PhysicsDebugRenderer()

    debug.render(
        renderer,
        root,
    )

    assert renderer.lines == []


def test_visible_debug_draws_shape():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    root.add_child(
        player
    )

    renderer = FakeRenderer()

    debug = PhysicsDebugRenderer()

    debug.visible = True

    debug.origins = False
    debug.velocity = False

    debug.render(
        renderer,
        root,
    )

    # Rectangle = 4 lines.
    assert len(
        renderer.lines
    ) == 4


def test_origin_adds_two_lines():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    root.add_child(
        player
    )

    renderer = FakeRenderer()

    debug = PhysicsDebugRenderer()

    debug.visible = True

    debug.shapes = False
    debug.velocity = False
    debug.origins = True

    debug.render(
        renderer,
        root,
    )

    assert len(
        renderer.lines
    ) == 2


def test_velocity_draws_line():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    player.velocity.set(
        100.0,
        50.0,
    )

    root.add_child(
        player
    )

    renderer = FakeRenderer()

    debug = PhysicsDebugRenderer()

    debug.visible = True

    debug.shapes = False
    debug.origins = False
    debug.velocity = True

    debug.render(
        renderer,
        root,
    )

    assert len(
        renderer.lines
    ) == 1


def test_zero_velocity_draws_no_vector():
    world = World()

    root = Node(
        "Root",
        world,
    )

    player = create_character(
        world
    )

    root.add_child(
        player
    )

    renderer = FakeRenderer()

    debug = PhysicsDebugRenderer()

    debug.visible = True

    debug.shapes = False
    debug.origins = False
    debug.velocity = True

    debug.render(
        renderer,
        root,
    )

    assert renderer.lines == []


def test_area_can_be_hidden():
    world = World()

    root = Node(
        "Root",
        world,
    )

    area = Area2D(
        "Interaction",
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

    root.add_child(
        area
    )

    renderer = FakeRenderer()

    debug = PhysicsDebugRenderer()

    debug.visible = True

    debug.areas = False

    debug.render(
        renderer,
        root,
    )

    assert renderer.lines == []


def test_disabled_shape_not_drawn():
    world = World()

    root = Node(
        "Root",
        world,
    )

    body = StaticBody2D(
        "Wall",
        world,
    )

    shape = CollisionShape2D(
        "Collision",
        world,
    )

    shape.disabled = True

    body.add_child(
        shape
    )

    root.add_child(
        body
    )

    renderer = FakeRenderer()

    debug = PhysicsDebugRenderer()

    debug.visible = True

    debug.origins = False

    debug.render(
        renderer,
        root,
    )

    assert renderer.lines == []


def test_toggle():
    debug = PhysicsDebugRenderer()

    assert not debug.visible

    assert debug.toggle()
    assert debug.visible

    assert not debug.toggle()
    assert not debug.visible

def test_collision_contact_draws_lines():
    from nexora.ecs.world import World

    from nexora.nodes import (
        CharacterBody2D,
        CollisionShape2D,
        Node,
        StaticBody2D,
    )

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
        "PlayerCollision",
        world,
        16.0,
        16.0,
    )

    player.add_child(
        player_shape
    )

    wall = StaticBody2D(
        "Wall",
        world,
    )

    wall.transform.x = 32.0

    wall_shape = CollisionShape2D(
        "WallCollision",
        world,
        32.0,
        32.0,
    )

    wall.add_child(
        wall_shape
    )

    root.add_child(
        player
    )

    root.add_child(
        wall
    )

    player.velocity.x = 100.0

    player.move_and_slide(
        1.0
    )

    renderer = FakeRenderer()

    debug = PhysicsDebugRenderer()

    debug.visible = True

    debug.shapes = False
    debug.origins = False
    debug.velocity = False

    debug.contacts = True
    debug.normals = False

    debug.render(
        renderer,
        root,
    )

    # Contact cross = 2 lines.
    assert len(
        renderer.lines
    ) == 2


def test_collision_normal_draws_arrow():
    from nexora.ecs.world import World

    from nexora.nodes import (
        CharacterBody2D,
        CollisionShape2D,
        Node,
        StaticBody2D,
    )

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
        "PlayerCollision",
        world,
        16.0,
        16.0,
    )

    player.add_child(
        player_shape
    )

    wall = StaticBody2D(
        "Wall",
        world,
    )

    wall.transform.x = 32.0

    wall_shape = CollisionShape2D(
        "WallCollision",
        world,
        32.0,
        32.0,
    )

    wall.add_child(
        wall_shape
    )

    root.add_child(
        player
    )

    root.add_child(
        wall
    )

    player.velocity.x = 100.0

    player.move_and_slide(
        1.0
    )

    renderer = FakeRenderer()

    debug = PhysicsDebugRenderer()

    debug.visible = True

    debug.shapes = False
    debug.origins = False
    debug.velocity = False

    debug.contacts = False
    debug.normals = True

    debug.render(
        renderer,
        root,
    )

    # Normal:
    #
    # main line
    # + two arrow-head lines
    #
    assert len(
        renderer.lines
    ) == 3


def test_collision_contact_and_normal():
    from nexora.ecs.world import World

    from nexora.nodes import (
        CharacterBody2D,
        CollisionShape2D,
        Node,
        StaticBody2D,
    )

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
        "PlayerCollision",
        world,
        16.0,
        16.0,
    )

    player.add_child(
        player_shape
    )

    wall = StaticBody2D(
        "Wall",
        world,
    )

    wall.transform.x = 32.0

    wall_shape = CollisionShape2D(
        "WallCollision",
        world,
        32.0,
        32.0,
    )

    wall.add_child(
        wall_shape
    )

    root.add_child(
        player
    )

    root.add_child(
        wall
    )

    player.velocity.x = 100.0

    player.move_and_slide(
        1.0
    )

    renderer = FakeRenderer()

    debug = PhysicsDebugRenderer()

    debug.visible = True

    debug.shapes = False
    debug.origins = False
    debug.velocity = False

    debug.contacts = True
    debug.normals = True

    debug.render(
        renderer,
        root,
    )

    # Contact cross:
    # 2 lines
    #
    # Normal arrow:
    # 3 lines
    #
    # Total:
    # 5

    assert len(
        renderer.lines
    ) == 5

def test_raycast_without_hit_draws_ray():
    from nexora.ecs.world import World
    from nexora.nodes import (
        Node,
        RayCast2D,
    )

    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = RayCast2D(
        "Ray",
        world,
        target_x=100.0,
        target_y=0.0,
    )

    root.add_child(
        ray
    )

    ray.force_raycast_update()

    renderer = FakeRenderer()

    debug = PhysicsDebugRenderer()

    debug.visible = True

    debug.shapes = False
    debug.origins = False
    debug.velocity = False
    debug.contacts = False
    debug.normals = False

    debug.rays = True

    debug.render(
        renderer,
        root,
    )

    # Origin cross = 2
    # Ray line     = 1
    # End cross    = 2
    #
    # Total        = 5

    assert len(
        renderer.lines
    ) == 5


def test_raycast_hit_draws_hit_and_normal():
    from nexora.ecs.world import World
    from nexora.nodes import (
        CollisionShape2D,
        Node,
        RayCast2D,
        StaticBody2D,
    )

    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = RayCast2D(
        "Ray",
        world,
        target_x=100.0,
        target_y=0.0,
    )

    wall = StaticBody2D(
        "Wall",
        world,
    )

    wall.transform.x = 50.0
    wall.transform.y = -16.0

    shape = CollisionShape2D(
        "Collision",
        world,
        32.0,
        32.0,
    )

    wall.add_child(
        shape
    )

    root.add_child(
        ray
    )

    root.add_child(
        wall
    )

    ray.force_raycast_update()

    assert ray.is_colliding

    renderer = FakeRenderer()

    debug = PhysicsDebugRenderer()

    debug.visible = True

    debug.shapes = False
    debug.origins = False
    debug.velocity = False
    debug.contacts = False
    debug.normals = False

    debug.rays = True
    debug.ray_hits = True

    debug.render(
        renderer,
        root,
    )

    # Origin cross       = 2
    # ray to hit         = 1
    # remaining ray      = 1
    # hit cross          = 2
    # normal line        = 1
    # normal arrow head  = 2
    #
    # Total              = 9

    assert len(
        renderer.lines
    ) == 9


def test_raycast_hit_can_hide_hit_details():
    from nexora.ecs.world import World
    from nexora.nodes import (
        CollisionShape2D,
        Node,
        RayCast2D,
        StaticBody2D,
    )

    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = RayCast2D(
        "Ray",
        world,
        target_x=100.0,
    )

    wall = StaticBody2D(
        "Wall",
        world,
    )

    wall.transform.x = 50.0
    wall.transform.y = -16.0

    wall.add_child(
        CollisionShape2D(
            "Collision",
            world,
            32.0,
            32.0,
        )
    )

    root.add_child(
        ray
    )

    root.add_child(
        wall
    )

    ray.force_raycast_update()

    renderer = FakeRenderer()

    debug = PhysicsDebugRenderer()

    debug.visible = True

    debug.shapes = False
    debug.origins = False
    debug.velocity = False
    debug.contacts = False
    debug.normals = False

    debug.rays = True
    debug.ray_hits = False

    debug.render(
        renderer,
        root,
    )

    # Origin cross  = 2
    # ray to hit    = 1
    # remaining ray = 1

    assert len(
        renderer.lines
    ) == 4


def test_raycast_debug_can_be_disabled():
    from nexora.ecs.world import World
    from nexora.nodes import (
        Node,
        RayCast2D,
    )

    world = World()

    root = Node(
        "Root",
        world,
    )

    ray = RayCast2D(
        "Ray",
        world,
    )

    root.add_child(
        ray
    )

    renderer = FakeRenderer()

    debug = PhysicsDebugRenderer()

    debug.visible = True
    debug.rays = False

    debug.shapes = False
    debug.origins = False

    debug.render(
        renderer,
        root,
    )

    assert renderer.lines == []