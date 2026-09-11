from nexora.ecs.component import Transform
from nexora.ecs.world import World
from nexora.scene.node import Node


def test_node_hierarchy():
    world = World()

    root = Node("Root", world)
    player = Node("Player", world)
    weapon = Node("Weapon", world)

    root.add_child(player)
    player.add_child(weapon)

    assert root.parent is None
    assert player.parent is root
    assert weapon.parent is player

    assert root.children == [player]
    assert player.children == [weapon]

    assert root.find_child("Player") is player
    assert root.find_child("Weapon") is weapon


def test_node_ecs_entities():
    world = World()

    root = Node("Root", world)
    player = Node("Player", world)
    weapon = Node("Weapon", world)

    assert world.is_alive(root.entity)
    assert world.is_alive(player.entity)
    assert world.is_alive(weapon.entity)


def test_node_transform_component():
    world = World()

    root = Node("Root", world)
    player = Node("Player", world)
    weapon = Node("Weapon", world)

    assert world.has_component(root.entity, Transform)
    assert world.has_component(player.entity, Transform)
    assert world.has_component(weapon.entity, Transform)

    assert root.transform.x == 0.0
    assert root.transform.y == 0.0
    assert root.transform.rotation == 0.0
    assert root.transform.scale_x == 1.0
    assert root.transform.scale_y == 1.0


def test_node_world_position():
    world = World()

    root = Node("Root", world)
    player = Node("Player", world)
    weapon = Node("Weapon", world)

    root.add_child(player)
    player.add_child(weapon)

    player.transform.x = 100.0
    player.transform.y = 100.0

    weapon.transform.x = 20.0
    weapon.transform.y = 0.0

    x, y = weapon.world_position

    assert x == 120.0
    assert y == 100.0


def test_node_destroy():
    world = World()

    root = Node("Root", world)
    player = Node("Player", world)
    weapon = Node("Weapon", world)

    root.add_child(player)
    player.add_child(weapon)

    player.destroy()

    assert not world.is_alive(player.entity)
    assert not world.is_alive(weapon.entity)
    assert root.children == []

def test_node_world_rotation_and_scale():
    world = World()

    root = Node("Root", world)
    player = Node("Player", world)
    weapon = Node("Weapon", world)

    root.add_child(player)
    player.add_child(weapon)

    player.transform.rotation = 45.0
    player.transform.scale_x = 2.0
    player.transform.scale_y = 2.0

    weapon.transform.rotation = 15.0
    weapon.transform.scale_x = 0.5
    weapon.transform.scale_y = 1.0

    assert weapon.world_rotation == 60.0

    scale_x, scale_y = weapon.world_scale

    assert scale_x == 1.0
    assert scale_y == 2.0

def test_node_world_transform():
    world = World()

    root = Node("Root", world)
    player = Node("Player", world)
    weapon = Node("Weapon", world)

    root.add_child(player)
    player.add_child(weapon)

    player.transform.x = 100.0
    player.transform.y = 100.0
    player.transform.rotation = 30.0
    player.transform.scale_x = 2.0
    player.transform.scale_y = 2.0

    weapon.transform.x = 20.0
    weapon.transform.y = 0.0
    weapon.transform.rotation = 15.0
    weapon.transform.scale_x = 0.5
    weapon.transform.scale_y = 1.0

    transform = weapon.world_transform

    assert transform.x == weapon.world_position[0]
    assert transform.y == weapon.world_position[1]
    assert transform.rotation == 45.0
    assert transform.scale_x == 1.0
    assert transform.scale_y == 2.0