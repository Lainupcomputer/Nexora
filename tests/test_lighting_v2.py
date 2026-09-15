from __future__ import annotations

import math

from nexora.ecs.world import World
from nexora.lighting import (
    LightSnapshot,
    LightingSystem,
    OccluderSnapshot,
)
from nexora.nodes import Light2D, LightOccluder2D
from nexora.rendering.camera import Camera
from nexora.scene.serialization.registry import NodeFactoryRegistry


class FakePostProcess:
    def __init__(self) -> None:
        self.enabled = False
        self.calls: list[dict] = []

    def enable(self) -> None:
        self.enabled = True

    def set_lighting(self, **kwargs) -> None:
        self.calls.append(kwargs)


def test_occluder_snapshot_builds_closed_polygon_segments():
    snapshot = OccluderSnapshot(
        points=((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)),
        closed=True,
    )

    segments = snapshot.segments()
    assert len(segments) == 4
    assert segments[0] == ((0.0, 0.0), (10.0, 0.0))
    assert segments[-1] == ((0.0, 10.0), (0.0, 0.0))


def test_light_occluder_uses_node_world_transform():
    world = World()
    parent = LightOccluder2D("Parent", world)
    child = LightOccluder2D("Child", world)
    parent.add_child(child)

    parent.transform.x = 100.0
    parent.transform.y = 50.0
    parent.transform.rotation = 90.0
    child.transform.x = 10.0
    child.set_segment((0.0, 0.0), (20.0, 0.0))

    points = child.snapshot().points
    assert math.isclose(points[0][0], 100.0, abs_tol=1e-6)
    assert math.isclose(points[0][1], 60.0, abs_tol=1e-6)
    assert math.isclose(points[1][0], 100.0, abs_tol=1e-6)
    assert math.isclose(points[1][1], 80.0, abs_tol=1e-6)


def test_shadow_segments_are_filtered_by_shadow_mask():
    lighting = LightingSystem()
    lighting.submit(
        LightSnapshot(
            0.0,
            0.0,
            200.0,
            1.0,
            (1.0, 1.0, 1.0),
            2.0,
            cast_shadows=True,
            shadow_mask=0b01,
        )
    )
    lighting.submit_occluder(
        OccluderSnapshot(
            points=((20.0, -20.0), (20.0, 20.0)),
            mask=0b01,
            closed=False,
        )
    )
    lighting.submit_occluder(
        OccluderSnapshot(
            points=((40.0, -20.0), (40.0, 20.0)),
            mask=0b10,
            closed=False,
        )
    )

    lights, segments = lighting.build_screen_frame(Camera(), 800, 600)
    assert len(lights) == 1
    assert len(segments) == 1
    assert lights[0].shadow_start == 0
    assert lights[0].shadow_count == 1


def test_non_shadow_light_does_not_allocate_segments():
    lighting = LightingSystem()
    lighting.submit(
        LightSnapshot(
            0.0,
            0.0,
            200.0,
            1.0,
            (1.0, 1.0, 1.0),
            2.0,
            cast_shadows=False,
        )
    )
    lighting.submit_occluder(
        OccluderSnapshot(
            points=((20.0, -20.0), (20.0, 20.0)),
            closed=False,
        )
    )

    lights, segments = lighting.build_screen_frame(Camera(), 800, 600)
    assert len(lights) == 1
    assert lights[0].shadow_count == 0
    assert segments == ()


def test_global_shadow_toggle_disables_segment_submission():
    lighting = LightingSystem()
    lighting.disable_shadows()
    lighting.submit(
        LightSnapshot(
            0.0,
            0.0,
            200.0,
            1.0,
            (1.0, 1.0, 1.0),
            2.0,
            cast_shadows=True,
        )
    )
    lighting.submit_occluder(
        OccluderSnapshot(
            points=((20.0, -20.0), (20.0, 20.0)),
            closed=False,
        )
    )

    lights, segments = lighting.build_screen_frame(Camera(), 800, 600)
    assert len(lights) == 1
    assert lights[0].shadow_count == 0
    assert segments == ()


def test_apply_passes_shadow_segments_to_post_process():
    lighting = LightingSystem()
    lighting.set_ambient((0.2, 0.2, 0.25), 0.4)
    lighting.submit(
        LightSnapshot(
            0.0,
            0.0,
            200.0,
            1.0,
            (1.0, 0.5, 0.2),
            2.0,
            cast_shadows=True,
            shadow_strength=0.8,
            shadow_softness=0.2,
        )
    )
    lighting.submit_occluder(
        OccluderSnapshot(
            points=((25.0, -20.0), (25.0, 20.0)),
            closed=False,
        )
    )

    post = FakePostProcess()
    lighting.apply(post, Camera(), 800, 600)

    assert post.enabled is True
    assert len(post.calls[-1]["lights"]) == 1
    assert len(post.calls[-1]["shadow_segments"]) == 1
    assert post.calls[-1]["lights"][0].shadow_strength == 0.8
    assert post.calls[-1]["lights"][0].shadow_softness == 0.2


def test_light2d_shadow_settings_serialization_roundtrip():
    world = World()
    light = Light2D("Lamp", world)
    light.cast_shadows = True
    light.shadow_strength = 0.72
    light.shadow_softness = 0.18
    light.shadow_color = (0.05, 0.02, 0.08)
    light.shadow_mask = 5

    registry = NodeFactoryRegistry()
    state = registry.dump_properties(light)
    restored = registry.create("Light2D", "Restored", world)
    registry.load_properties(restored, state)

    assert restored.cast_shadows is True
    assert restored.shadow_strength == 0.72
    assert restored.shadow_softness == 0.18
    assert restored.shadow_color == (0.05, 0.02, 0.08)
    assert restored.shadow_mask == 5


def test_light_occluder_serialization_roundtrip():
    world = World()
    occluder = LightOccluder2D("Wall", world)
    occluder.set_polygon(((-40.0, -10.0), (40.0, -10.0), (40.0, 10.0), (-40.0, 10.0)))
    occluder.occluder_mask = 3
    occluder.debug_draw = True

    registry = NodeFactoryRegistry()
    state = registry.dump_properties(occluder)
    restored = registry.create("LightOccluder2D", "Restored", world)
    registry.load_properties(restored, state)

    assert restored.points == occluder.points
    assert restored.closed is True
    assert restored.occluder_mask == 3
    assert restored.debug_draw is True
