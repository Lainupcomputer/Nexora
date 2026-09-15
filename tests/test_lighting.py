from __future__ import annotations

import math

from nexora.ecs.world import World
from nexora.lighting import LightSnapshot, LightingSystem
from nexora.nodes import Light2D
from nexora.rendering.camera import Camera
from nexora.scene.serialization.registry import NodeFactoryRegistry


class FakePostProcess:
    def __init__(self):
        self.enabled = False
        self.calls = []

    def enable(self):
        self.enabled = True

    def set_lighting(self, **kwargs):
        self.calls.append(kwargs)


def test_light_snapshot_validates_values():
    LightSnapshot(0, 0, 10, 1, (1, 1, 1), 2)


def test_lighting_system_filters_mask_and_limit():
    lighting = LightingSystem(max_lights=1)
    lighting.visible_mask = 0b01

    assert lighting.submit(LightSnapshot(0, 0, 10, 1, (1, 1, 1), 2, mask=0b10)) is False
    assert lighting.submit(LightSnapshot(0, 0, 10, 1, (1, 1, 1), 2, mask=0b01)) is True
    assert lighting.submit(LightSnapshot(0, 0, 10, 1, (1, 1, 1), 2, mask=0b01)) is False
    assert lighting.light_count == 1


def test_screen_light_uses_camera_and_zoom():
    lighting = LightingSystem()
    camera = Camera(x=0.0, y=0.0, zoom=2.0)
    lighting.submit(LightSnapshot(10, 20, 50, 1.5, (1, 0.5, 0.25), 2.0))

    lights = lighting.screen_lights(camera, 800, 600)
    assert len(lights) == 1
    light = lights[0]
    assert light.x == 420.0
    assert light.y == 340.0
    assert light.radius == 100.0
    assert light.intensity == 1.5


def test_apply_enables_post_process_and_passes_ambient():
    lighting = LightingSystem()
    lighting.set_ambient((0.2, 0.3, 0.4), 0.5)
    post = FakePostProcess()
    camera = Camera()

    lighting.apply(post, camera, 800, 600)

    assert post.enabled
    assert post.calls[-1]["enabled"] is True
    assert post.calls[-1]["ambient_color"] == (0.2, 0.3, 0.4)
    assert post.calls[-1]["ambient_intensity"] == 0.5


def test_light2d_submits_world_position_and_effective_intensity():
    world = World()
    parent = Light2D("Parent", world)
    child = Light2D("Child", world)
    parent.add_child(child)
    parent.transform.x = 100.0
    parent.transform.y = 50.0
    child.transform.x = 10.0
    child.transform.y = 5.0
    child.intensity = 2.0

    snap = child.snapshot()
    assert snap.x == 110.0
    assert snap.y == 55.0
    assert snap.intensity == 2.0


def test_light2d_pulse_changes_intensity():
    world = World()
    light = Light2D("Pulse", world)
    light.intensity = 1.0
    light.pulse_enabled = True
    light.pulse_amount = 0.5
    light.pulse_speed = 1.0

    before = light.effective_intensity
    light.update(0.25)
    after = light.effective_intensity
    assert not math.isclose(before, after)


def test_light2d_serialization_roundtrip():
    world = World()
    light = Light2D("Lamp", world)
    light.color = (0.2, 0.4, 0.8)
    light.radius = 333.0
    light.intensity = 1.75
    light.falloff = 3.0
    light.light_mask = 7
    light.flicker_enabled = True
    light.pulse_enabled = True

    registry = NodeFactoryRegistry()
    state = registry.dump_properties(light)
    restored = registry.create("Light2D", "Restored", world)
    registry.load_properties(restored, state)

    assert restored.color == (0.2, 0.4, 0.8)
    assert restored.radius == 333.0
    assert restored.intensity == 1.75
    assert restored.falloff == 3.0
    assert restored.light_mask == 7
    assert restored.flicker_enabled is True
    assert restored.pulse_enabled is True
