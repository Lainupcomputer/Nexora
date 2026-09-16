from __future__ import annotations

import math
from types import SimpleNamespace

from nexora.editor.commands import (
    TransformNodeCommand,
    TransformSnapshot,
)
from nexora.editor.viewport import (
    GIZMO_MOVE,
    GIZMO_ROTATE,
    GIZMO_SCALE,
    EditorViewportState,
    drag_angle_degrees,
    gizmo_hit_test,
    world_delta_to_local,
)


class DummyNode:
    def __init__(self):
        self.transform = SimpleNamespace(
            x=10.0,
            y=20.0,
            rotation=30.0,
            scale_x=1.5,
            scale_y=2.0,
        )
        self.parent = None


def test_transform_snapshot_apply_and_command_undo():
    node = DummyNode()

    before = TransformSnapshot.from_node(node)

    node.transform.x = 99.0
    node.transform.rotation = 90.0

    after = TransformSnapshot.from_node(node)

    command = TransformNodeCommand(
        node,
        before,
        after,
        label="Move Node",
    )

    command.undo()

    assert node.transform.x == 10.0
    assert node.transform.rotation == 30.0

    command.execute()

    assert node.transform.x == 99.0
    assert node.transform.rotation == 90.0


def test_move_gizmo_hit_test():
    assert gizmo_hit_test(
        GIZMO_MOVE,
        mouse_x=55.0,
        mouse_y=0.0,
        pivot_x=0.0,
        pivot_y=0.0,
    ) == "x"

    assert gizmo_hit_test(
        GIZMO_MOVE,
        mouse_x=0.0,
        mouse_y=55.0,
        pivot_x=0.0,
        pivot_y=0.0,
    ) == "y"

    assert gizmo_hit_test(
        GIZMO_MOVE,
        mouse_x=2.0,
        mouse_y=-1.0,
        pivot_x=0.0,
        pivot_y=0.0,
    ) == "xy"


def test_scale_gizmo_center_is_uniform():
    assert gizmo_hit_test(
        GIZMO_SCALE,
        mouse_x=0.0,
        mouse_y=0.0,
        pivot_x=0.0,
        pivot_y=0.0,
    ) == "uniform"


def test_rotate_gizmo_hit_test():
    assert gizmo_hit_test(
        GIZMO_ROTATE,
        mouse_x=54.0,
        mouse_y=0.0,
        pivot_x=0.0,
        pivot_y=0.0,
    ) == "rotate"

    assert gizmo_hit_test(
        GIZMO_ROTATE,
        mouse_x=20.0,
        mouse_y=0.0,
        pivot_x=0.0,
        pivot_y=0.0,
    ) is None


def test_drag_angle():
    assert math.isclose(
        drag_angle_degrees(
            1.0,
            0.0,
            0.0,
            0.0,
        ),
        0.0,
    )

    assert math.isclose(
        drag_angle_degrees(
            0.0,
            1.0,
            0.0,
            0.0,
        ),
        90.0,
    )


def test_world_delta_to_local_without_parent():
    node = DummyNode()

    assert world_delta_to_local(
        node,
        10.0,
        -5.0,
    ) == (
        10.0,
        -5.0,
    )


def test_world_delta_to_local_respects_parent_rotation_and_scale():
    node = DummyNode()

    node.parent = SimpleNamespace(
        world_rotation=90.0,
        world_scale=(2.0, 4.0),
    )

    local_x, local_y = world_delta_to_local(
        node,
        0.0,
        8.0,
    )

    assert math.isclose(
        local_x,
        4.0,
        abs_tol=1e-7,
    )

    assert math.isclose(
        local_y,
        0.0,
        abs_tol=1e-7,
    )


def test_viewport_zoom_at_keeps_world_point_stable():
    state = EditorViewportState()

    before = state.screen_to_world(
        100.0,
        40.0,
        0.0,
        0.0,
    )

    state.zoom_at(
        100.0,
        40.0,
        0.0,
        0.0,
        2.0,
    )

    after = state.screen_to_world(
        100.0,
        40.0,
        0.0,
        0.0,
    )

    assert math.isclose(
        before[0],
        after[0],
    )

    assert math.isclose(
        before[1],
        after[1],
    )
