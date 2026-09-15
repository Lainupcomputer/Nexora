from __future__ import annotations

import math

from nexora.ecs.world import World
from nexora.nodes import (
    CharacterBody2D,
    NavigationAgent2D,
    TileMapNode,
)
from nexora.scene.serialization.registry import (
    NodeFactoryRegistry,
)
from nexora.tilemap import (
    NavigationAvoidanceState,
    TileMap,
    TileSet,
)


def make_map():
    world = World()

    tilemap = TileMap(
        width=10,
        height=5,
        tile_width=64,
        tile_height=32,
        projection="isometric",
    )

    layer = tilemap.create_layer(
        "ground"
    )

    for y in range(
        tilemap.height
    ):
        for x in range(
            tilemap.width
        ):
            layer.set_tile(
                x,
                y,
                0,
            )

    tileset = TileSet(
        columns=1,
        rows=1,
        tile_width=64,
        tile_height=32,
    )

    map_node = TileMapNode(
        "World",
        world,
    )

    map_node.tilemap = tilemap
    map_node.tileset = tileset
    map_node.centered = False

    return (
        world,
        map_node,
    )


def make_agent(
    world,
    map_node,
    name,
    start,
    target,
):
    body = CharacterBody2D(
        name,
        world,
    )

    agent = NavigationAgent2D(
        f"{name}Agent",
        world,
    )

    body.add_child(
        agent
    )

    body.transform.x, body.transform.y = (
        map_node.tile_world_position(
            *start
        )
    )

    agent.configure(
        map_node,
        layer_name="ground",
    )

    agent.set_target_position(
        *map_node.tile_world_position(
            *target
        )
    )

    path = agent.request_path()

    assert path is not None

    agent.update(
        0.016
    )

    return (
        body,
        agent,
    )


def test_avoidance_state_ignores_self_and_far_agents():
    state = NavigationAvoidanceState()

    state.register(
        1,
        position=(0.0, 0.0),
        radius=10.0,
    )

    state.register(
        2,
        position=(20.0, 0.0),
        radius=10.0,
    )

    state.register(
        3,
        position=(200.0, 0.0),
        radius=10.0,
    )

    neighbors = state.neighbors(
        1,
        distance=50.0,
    )

    assert [
        item.owner_id
        for item in neighbors
    ] == [2]


def test_single_agent_velocity_is_unchanged():
    world, map_node = make_map()

    _, agent = make_agent(
        world,
        map_node,
        "A",
        (1, 2),
        (8, 2),
    )

    preferred = (
        agent.preferred_velocity(
            100.0
        )
    )

    desired = (
        agent.desired_velocity(
            100.0
        )
    )

    assert math.isclose(
        desired[0],
        preferred[0],
        abs_tol=1e-6,
    )

    assert math.isclose(
        desired[1],
        preferred[1],
        abs_tol=1e-6,
    )


def test_two_head_on_agents_receive_avoidance_steering():
    world, map_node = make_map()

    body_a, agent_a = make_agent(
        world,
        map_node,
        "A",
        (2, 2),
        (7, 2),
    )

    body_b, agent_b = make_agent(
        world,
        map_node,
        "B",
        (7, 2),
        (2, 2),
    )

    # ------------------------------------------------------
    # Teleport both agents close enough that their predicted
    # movement paths conflict.
    # ------------------------------------------------------

    ax, ay = (
        map_node.tile_world_position(
            4,
            2,
        )
    )

    bx, by = (
        map_node.tile_world_position(
            5,
            2,
        )
    )

    body_a.transform.x = ax
    body_a.transform.y = ay

    body_b.transform.x = bx
    body_b.transform.y = by

    # ------------------------------------------------------
    # IMPORTANT:
    #
    # Both bodies were moved after the original paths were
    # calculated.
    #
    # Rebuild those paths so their current waypoint starts
    # from the new body position.
    # ------------------------------------------------------

    path_a = agent_a.request_path()
    path_b = agent_b.request_path()

    assert path_a is not None
    assert path_b is not None

    # ------------------------------------------------------
    # Publish velocities representing their intended movement.
    # ------------------------------------------------------

    preferred_a = (
        agent_a.preferred_velocity(
            100.0
        )
    )

    preferred_b = (
        agent_b.preferred_velocity(
            100.0
        )
    )

    body_a.velocity.set(
        *preferred_a
    )

    body_b.velocity.set(
        *preferred_b
    )

    # ------------------------------------------------------
    # Update both shared avoidance snapshots.
    # ------------------------------------------------------

    agent_a.update(
        0.016
    )

    agent_b.update(
        0.016
    )

    # Re-read preferred velocities after update so both values
    # represent the current path-following state.
    preferred_a = (
        agent_a.preferred_velocity(
            100.0
        )
    )

    preferred_b = (
        agent_b.preferred_velocity(
            100.0
        )
    )

    desired_a = (
        agent_a.desired_velocity(
            100.0
        )
    )

    desired_b = (
        agent_b.desired_velocity(
            100.0
        )
    )

    assert desired_a != preferred_a
    assert desired_b != preferred_b

    assert (
        math.hypot(
            *desired_a
        )
        <= 100.000001
    )

    assert (
        math.hypot(
            *desired_b
        )
        <= 100.000001
    )


def test_avoidance_can_be_disabled_per_agent():
    world, map_node = make_map()

    body_a, agent_a = make_agent(
        world,
        map_node,
        "A",
        (2, 2),
        (7, 2),
    )

    body_b, agent_b = make_agent(
        world,
        map_node,
        "B",
        (7, 2),
        (2, 2),
    )

    ax, ay = (
        map_node.tile_world_position(
            4,
            2,
        )
    )

    bx, by = (
        map_node.tile_world_position(
            5,
            2,
        )
    )

    body_a.transform.x = ax
    body_a.transform.y = ay

    body_b.transform.x = bx
    body_b.transform.y = by

    # Bodies were teleported, therefore rebuild their paths.
    assert agent_a.request_path() is not None
    assert agent_b.request_path() is not None

    agent_a.avoidance_enabled = False

    body_a.velocity.set(
        *agent_a.preferred_velocity(
            90.0
        )
    )

    body_b.velocity.set(
        *agent_b.preferred_velocity(
            90.0
        )
    )

    agent_a.update(
        0.016
    )

    agent_b.update(
        0.016
    )

    assert (
        agent_a.desired_velocity(
            90.0
        )
        ==
        agent_a.preferred_velocity(
            90.0
        )
    )


def test_destroy_unregisters_agent_from_shared_state():
    world, map_node = make_map()

    _, agent = make_agent(
        world,
        map_node,
        "A",
        (1, 2),
        (8, 2),
    )

    owner_id = (
        agent._avoidance_owner_id
    )

    assert (
        map_node.avoidance_state.snapshot(
            owner_id
        )
        is not None
    )

    agent.destroy()

    assert (
        map_node.avoidance_state.snapshot(
            owner_id
        )
        is None
    )


def test_agent_serialization_preserves_avoidance_settings():
    world, map_node = make_map()

    _, agent = make_agent(
        world,
        map_node,
        "A",
        (1, 2),
        (8, 2),
    )

    agent.avoidance_enabled = False
    agent.avoidance_radius = 18.0
    agent.avoidance_neighbor_distance = 96.0
    agent.avoidance_time_horizon = 1.25
    agent.avoidance_strength = 0.6

    registry = NodeFactoryRegistry()

    state = (
        registry.dump_properties(
            agent
        )
    )

    restored = registry.create(
        "NavigationAgent2D",
        "Restored",
        world,
    )

    registry.load_properties(
        restored,
        state,
    )

    assert (
        restored.avoidance_enabled
        is False
    )

    assert (
        restored.avoidance_radius
        == 18.0
    )

    assert (
        restored.avoidance_neighbor_distance
        == 96.0
    )

    assert (
        restored.avoidance_time_horizon
        == 1.25
    )

    assert (
        restored.avoidance_strength
        == 0.6
    )