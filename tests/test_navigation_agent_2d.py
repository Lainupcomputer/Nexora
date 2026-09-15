from nexora.ecs.world import World
from nexora.nodes import CharacterBody2D, NavigationAgent2D, TileMapNode
from nexora.scene.serialization.registry import NodeFactoryRegistry
from nexora.tilemap import TileMap, TileSet


def make_world():
    world = World()
    tilemap = TileMap(
        width=6,
        height=6,
        tile_width=64,
        tile_height=32,
        projection="isometric",
    )
    layer = tilemap.create_layer("ground")
    for y in range(6):
        for x in range(6):
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
    agent = NavigationAgent2D("NavigationAgent", world)
    body.add_child(agent)

    return world, map_node, body, agent


def test_agent_is_node_and_uses_parent_character_body():
    _, map_node, body, agent = make_world()
    agent.configure(map_node, layer_name="ground")

    body.transform.x, body.transform.y = map_node.tile_world_position(0, 0)
    target = map_node.tile_world_position(3, 0)
    agent.set_target_position(*target)

    path = agent.request_path()

    assert path is not None
    assert agent.body is body
    assert agent.current_waypoint is not None
    assert agent.desired_direction != (0.0, 0.0)


def test_agent_does_not_move_body_itself():
    _, map_node, body, agent = make_world()
    agent.configure(map_node, layer_name="ground")

    body.transform.x, body.transform.y = map_node.tile_world_position(0, 0)
    before = body.world_position
    agent.set_target_position(*map_node.tile_world_position(2, 0))
    agent.update(0.016)

    assert body.world_position == before
    vx, vy = agent.desired_velocity(100.0)
    assert (vx, vy) != (0.0, 0.0)


def test_agent_advances_waypoints_and_emits_target_reached():
    _, map_node, body, agent = make_world()
    agent.configure(map_node, layer_name="ground")
    body.transform.x, body.transform.y = map_node.tile_world_position(0, 0)

    reached = []
    agent.connect_target_reached(lambda value: reached.append(value))

    target = map_node.tile_world_position(2, 0)
    agent.set_target_position(*target)
    agent.request_path()

    body.transform.x, body.transform.y = target
    agent.update(0.016)

    assert agent.target_reached
    assert reached == [agent]
    assert agent.desired_direction == (0.0, 0.0)


def test_agent_repaths_after_navigation_revision_changes():
    _, map_node, body, agent = make_world()
    navigation = agent.configure(map_node, layer_name="ground")
    body.transform.x, body.transform.y = map_node.tile_world_position(0, 0)
    agent.set_target_position(*map_node.tile_world_position(4, 0))
    agent.request_path()
    first_path = agent.path

    navigation.set_blocked(1, 0, True)
    agent.update(0.016)

    assert agent.path is not None
    assert agent.path is not first_path
    assert (1, 0) not in agent.path.tiles


def test_agent_serialization_preserves_configuration():
    world, _, _, agent = make_world()
    agent.map_node_name = "World"
    agent.layer_name = "ground"
    agent.allow_diagonal = True
    agent.waypoint_tolerance = 7.0
    agent.target_tolerance = 9.0
    agent.repath_interval = 0.5
    agent.set_target_position(100.0, 200.0)

    registry = NodeFactoryRegistry()
    state = registry.dump_properties(agent)
    restored = registry.create("NavigationAgent2D", "Agent", world)
    registry.load_properties(restored, state)

    assert restored.map_node_name == "World"
    assert restored.allow_diagonal is True
    assert restored.waypoint_tolerance == 7.0
    assert restored.target_tolerance == 9.0
    assert restored.repath_interval == 0.5
    assert restored.target_position == (100.0, 200.0)
