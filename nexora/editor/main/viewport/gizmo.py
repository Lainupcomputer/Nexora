from __future__ import annotations

from math import atan2, cos, degrees, hypot, radians, sin

GIZMO_MOVE = "move"
GIZMO_ROTATE = "rotate"
GIZMO_SCALE = "scale"

_GIZMO_AXIS_LENGTH = 72.0
_GIZMO_HIT_RADIUS = 9.0
_GIZMO_ROTATE_RADIUS = 54.0

def _distance_to_segment(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:
    """Return the screen-space distance from a point to a line segment."""

    dx = x2 - x1
    dy = y2 - y1

    length_sq = dx * dx + dy * dy

    if length_sq <= 1e-12:
        return hypot(
            px - x1,
            py - y1,
        )

    t = (
        (px - x1) * dx
        + (py - y1) * dy
    ) / length_sq

    t = max(
        0.0,
        min(
            1.0,
            t,
        ),
    )

    nearest_x = x1 + dx * t
    nearest_y = y1 + dy * t

    return hypot(
        px - nearest_x,
        py - nearest_y,
    )

def gizmo_hit_test(
    mode: str,
    *,
    mouse_x: float,
    mouse_y: float,
    pivot_x: float,
    pivot_y: float,
) -> str | None:
    """Return the transform gizmo handle under the pointer."""

    mode = str(
        mode
    ).lower()

    if mode == GIZMO_ROTATE:
        distance = hypot(
            mouse_x - pivot_x,
            mouse_y - pivot_y,
        )

        if (
            abs(
                distance
                - _GIZMO_ROTATE_RADIUS
            )
            <= _GIZMO_HIT_RADIUS
        ):
            return "rotate"

        return None

    # Small center handle allows free move / uniform scale.
    if (
        abs(mouse_x - pivot_x) <= 8.0
        and abs(mouse_y - pivot_y) <= 8.0
    ):
        if mode == GIZMO_SCALE:
            return "uniform"

        return "xy"

    x_distance = _distance_to_segment(
        mouse_x,
        mouse_y,
        pivot_x + 10.0,
        pivot_y,
        pivot_x + _GIZMO_AXIS_LENGTH,
        pivot_y,
    )

    y_distance = _distance_to_segment(
        mouse_x,
        mouse_y,
        pivot_x,
        pivot_y + 10.0,
        pivot_x,
        pivot_y + _GIZMO_AXIS_LENGTH,
    )

    if (
        x_distance <= _GIZMO_HIT_RADIUS
        and x_distance <= y_distance
    ):
        return "x"

    if y_distance <= _GIZMO_HIT_RADIUS:
        return "y"

    return None

def world_delta_to_local(
    node,
    dx: float,
    dy: float,
) -> tuple[float, float]:
    """Convert a world-space movement delta into the node parent's space."""

    parent = getattr(
        node,
        "parent",
        None,
    )

    if parent is None:
        return float(dx), float(dy)

    try:
        rotation = radians(
            float(
                parent.world_rotation
            )
        )

        scale_x, scale_y = (
            parent.world_scale
        )

        scale_x = float(
            scale_x
        )
        scale_y = float(
            scale_y
        )

    except Exception:
        return float(dx), float(dy)

    # Inverse parent rotation.
    cos_angle = cos(
        rotation
    )
    sin_angle = sin(
        rotation
    )

    local_x = (
        float(dx) * cos_angle
        + float(dy) * sin_angle
    )

    local_y = (
        -float(dx) * sin_angle
        + float(dy) * cos_angle
    )

    if abs(scale_x) > 1e-9:
        local_x /= scale_x

    if abs(scale_y) > 1e-9:
        local_y /= scale_y

    return local_x, local_y

def drag_angle_degrees(
    mouse_x: float,
    mouse_y: float,
    pivot_x: float,
    pivot_y: float,
) -> float:
    """Angle of a pointer around a gizmo pivot in screen coordinates."""

    return degrees(
        atan2(
            mouse_y - pivot_y,
            mouse_x - pivot_x,
        )
    )
