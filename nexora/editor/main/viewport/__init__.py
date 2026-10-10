"""Editor viewport state, gizmos, picking, rendering, and canvas support.

This package preserves the public imports previously provided by
``nexora.editor.main.viewport`` while keeping each viewport responsibility in
a focused module.
"""

from .canvas import EditorViewportCanvas
from .gizmo import (
    GIZMO_MOVE,
    GIZMO_ROTATE,
    GIZMO_SCALE,
    drag_angle_degrees,
    gizmo_hit_test,
    world_delta_to_local,
)
from .picking import node_hit_distance
from .renderer import EditorViewportRenderer
from .state import EditorViewportState

__all__ = [
    "EditorViewportCanvas",
    "EditorViewportRenderer",
    "EditorViewportState",
    "GIZMO_MOVE",
    "GIZMO_ROTATE",
    "GIZMO_SCALE",
    "drag_angle_degrees",
    "gizmo_hit_test",
    "node_hit_distance",
    "world_delta_to_local",
]
