from nexora.ecs.world import World
from nexora.nodes import (
    CharacterBody2D,
    NavigationAgent2D,
    NavigationObstacle2D,
    TileMapNode,
)
from nexora.scene.serialization.registry import NodeFactoryRegistry
from nexora.tilemap import TileMap, TileSet


def make_world():
    world = World()
    tilemap = TileMap(
        width=7,
        height=5,
        tile_width=64,
        tile_height=32,
        projection="isometric",
    )
    layer = tilemap.create_layer("ground")
    for y in range(tilemap.height):
        for x in range(tilemap.width):
            layer.set_tile(x, y, 0)

    tileset = TileSet(
        columns=1,
        rows=1,
        tile_width=64,
        tile_height=32,
    )

    map_node = TileMapNode("World", world)
    map_node.tilemap = tilemap
    map_node.tileset = tileset
    map_node.centered = False

    body = CharacterBody2D("NPC", world)
    agent = NavigationAgent2D("Agent", world)
    body.add_child(agent)
    agent.configure(map_node, layer_name="ground")

    return world, map_node, body, agent


def place(node, map_node, x, y):
    node.transform.x, node.transform.y = map_node.tile_world_position(x, y)


def test_obstacle_uses_shared_navigation_state():
    world, map_node, body, agent = make_world()
    place(body, map_node, 0, 2)
    agent.set_target_position(*map_node.tile_world_position(6, 2))
    original = agent.request_path()
    assert original is not None
    assert (3, 2) in original.tiles

    obstacle = NavigationObstacle2D("Crate", world)
    place(obstacle, map_node, 3, 2)
    obstacle.configure(map_node)

    assert agent.navigation is not None
    assert (3, 2) in agent.navigation.dynamic_blockers

    agent.update(0.016)
    assert agent.path is not None
    assert (3, 2) not in agent.path.tiles


def test_moving_obstacle_invalidates_and_repaths():
    world, map_node, body, agent = make_world()
    place(body, map_node, 0, 2)
    agent.set_target_position(*map_node.tile_world_position(6, 2))

    obstacle = NavigationObstacle2D("Mover", world)
    place(obstacle, map_node, 3, 2)
    obstacle.configure(map_node)
    agent.request_path()
    blocked_path = agent.path
    revision = map_node.navigation_state.revision

    place(obstacle, map_node, 3, 1)
    assert obstacle.sync_blocking()
    assert map_node.navigation_state.revision > revision

    agent.update(0.016)
    assert agent.path is not None
    assert agent.path is not blocked_path
    assert (3, 2) in agent.path.tiles
    assert (3, 1) not in agent.path.tiles


def test_overlapping_obstacles_do_not_unblock_each_other():
    world, map_node, _, agent = make_world()
    first = NavigationObstacle2D("First", world)
    second = NavigationObstacle2D("Second", world)
    place(first, map_node, 2, 2)
    place(second, map_node, 2, 2)
    first.configure(map_node)
    second.configure(map_node)

    assert agent.navigation is not None
    assert (2, 2) in agent.navigation.dynamic_blockers

    place(first, map_node, 1, 2)
    first.sync_blocking()
    assert (2, 2) in agent.navigation.dynamic_blockers

    second.destroy()
    assert (2, 2) not in agent.navigation.dynamic_blockers


def test_obstacle_radius_blocks_square_footprint():
    world, map_node, _, agent = make_world()
    obstacle = NavigationObstacle2D("Large", world)
    obstacle.radius_tiles = 1
    place(obstacle, map_node, 3, 2)
    obstacle.configure(map_node)

    assert agent.navigation is not None
    expected = {
        (x, y)
        for y in range(1, 4)
        for x in range(2, 5)
    }
    assert obstacle.blocked_tiles == expected
    assert expected.issubset(agent.navigation.dynamic_blockers)


def test_obstacle_serialization_preserves_configuration():
    world, _, _, _ = make_world()
    obstacle = NavigationObstacle2D("Door", world)
    obstacle.map_node_name = "World"
    obstacle.radius_tiles = 2
    obstacle.blocking_enabled = False

    registry = NodeFactoryRegistry()
    state = registry.dump_properties(obstacle)
    restored = registry.create("NavigationObstacle2D", "Door", world)
    registry.load_properties(restored, state)

    assert restored.map_node_name == "World"
    assert restored.radius_tiles == 2
    assert restored.blocking_enabled is False
