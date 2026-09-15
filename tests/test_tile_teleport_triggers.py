from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from nexora.ecs.world import World
from nexora.nodes.world.tilemap_node import TileMapNode
from nexora.scene.manager import SceneManager
from nexora.tilemap import TileMap, TileMetadata, TileSet, TileTeleportEvent


class DummyActor:
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

    @property
    def world_position(self):
        return self.x, self.y


class FakeSceneManager:
    def __init__(self):
        self.calls = []

    def resolve_serialized_scene_name(self, reference):
        assert reference == "beach.nxscene"
        return "Beach"

    def begin_serialized_loading(self, name, **kwargs):
        self.calls.append((name, kwargs))
        return object()


def build_node():
    world = World()
    node = TileMapNode("World", world)

    tilemap = TileMap(
        width=4,
        height=4,
        tile_width=64,
        tile_height=32,
        projection="isometric",
    )
    ground = tilemap.create_layer("ground")
    ground.set_tile(1, 2, 3)

    tileset = TileSet(
        columns=4,
        rows=4,
        tile_width=64,
        tile_height=32,
        texture_asset="world/test.png",
    )

    meta = TileMetadata()
    meta.teleport = "beach.nxscene"
    tileset.set_metadata(3, meta)

    node.tilemap = tilemap
    node.tileset = tileset
    node.texture = object()
    return node


def place_actor_on(node, actor, x, y):
    actor.x, actor.y = node.tile_world_position(x, y)


def test_teleport_fires_once_on_tile_enter():
    node = build_node()
    actor = DummyActor()
    manager = FakeSceneManager()
    place_actor_on(node, actor, 1, 2)

    event = node.process_tile_triggers(
        actor,
        manager,
        layer_name="ground",
    )

    assert isinstance(event, TileTeleportEvent)
    assert event.scene_name == "Beach"
    assert event.reference == "beach.nxscene"
    assert len(manager.calls) == 1

    # Same tile, next frame: no repeated transition.
    assert node.process_tile_triggers(
        actor,
        manager,
        layer_name="ground",
    ) is None
    assert len(manager.calls) == 1


def test_teleport_can_fire_again_after_leaving_and_reentering():
    node = build_node()
    actor = DummyActor()
    manager = FakeSceneManager()

    place_actor_on(node, actor, 1, 2)
    assert node.process_tile_triggers(actor, manager, layer_name="ground")

    place_actor_on(node, actor, 0, 0)
    assert node.process_tile_triggers(actor, manager, layer_name="ground") is None

    place_actor_on(node, actor, 1, 2)
    assert node.process_tile_triggers(actor, manager, layer_name="ground")
    assert len(manager.calls) == 2


def test_teleport_metadata_overrides_loading_options():
    node = build_node()
    actor = DummyActor()
    manager = FakeSceneManager()
    meta = node.tileset.get_metadata(3)
    meta.set_property("teleport_loading_scene", "CustomLoading")
    meta.set_property("teleport_unload_previous", True)
    meta.set_property("teleport_force_reload_assets", True)
    meta.set_property("teleport_context", {"spawn": "west_gate"})

    place_actor_on(node, actor, 1, 2)
    node.process_tile_triggers(
        actor,
        manager,
        layer_name="ground",
        context={"difficulty": "hard"},
    )

    name, kwargs = manager.calls[0]
    assert name == "Beach"
    assert kwargs["loading_scene"] == "CustomLoading"
    assert kwargs["unload_previous"] is True
    assert kwargs["force_reload_assets"] is True
    assert kwargs["context"] == {
        "difficulty": "hard",
        "spawn": "west_gate",
    }


def test_scene_manager_resolves_registered_nxscene_by_name_or_path(tmp_path):
    manager = SceneManager()
    path = (tmp_path / "beach.nxscene").resolve()
    manager._serialized_registrations["Beach"] = SimpleNamespace(path=path)

    assert manager.resolve_serialized_scene_name("Beach") == "Beach"
    assert manager.resolve_serialized_scene_name(path) == "Beach"
    assert manager.resolve_serialized_scene_name("beach.nxscene") == "Beach"

    with pytest.raises(KeyError):
        manager.resolve_serialized_scene_name("missing.nxscene")
