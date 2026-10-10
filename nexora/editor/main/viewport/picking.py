from __future__ import annotations

from math import hypot

from .state import EditorViewportState

def node_hit_distance(
    node,
    *,
    mouse_x: float,
    mouse_y: float,
    state: EditorViewportState,
    center_x: float,
    center_y: float,
) -> float | None:
    """Return screen-space hit distance for one node, or None."""

    if not getattr(node, "visible", True):
        return None

    try:
        world_x, world_y = node.world_position
    except Exception:
        return None

    sx, sy = state.world_to_screen(
        world_x,
        world_y,
        center_x,
        center_y,
    )

    width = getattr(node, "width", 0.0)
    height = getattr(node, "height", 0.0)
    try:
        scale_x, scale_y = node.world_scale
        width = abs(float(width) * float(scale_x) * state.zoom)
        height = abs(float(height) * float(scale_y) * state.zoom)
    except (TypeError, ValueError, AttributeError):
        width = height = 0.0

    half_w = max(9.0, width * 0.5)
    half_h = max(9.0, height * 0.5)

    if (
        sx - half_w <= mouse_x <= sx + half_w
        and sy - half_h <= mouse_y <= sy + half_h
    ):
        return hypot(mouse_x - sx, mouse_y - sy)

    return None
