from __future__ import annotations

import math


def calculate_distance(
    source_position: tuple[float, float],
    listener_position: tuple[float, float],
) -> float:
    """Calculate the distance between source and listener."""

    dx = source_position[0] - listener_position[0]
    dy = source_position[1] - listener_position[1]

    return math.hypot(dx, dy)


def calculate_distance_attenuation(
    distance: float,
    min_distance: float,
    max_distance: float,
) -> float:
    """Calculate volume attenuation based on distance."""

    if min_distance <= 0.0:
        raise ValueError(
            "Minimum distance must be greater than 0."
        )

    if max_distance <= 0.0:
        raise ValueError(
            "Maximum distance must be greater than 0."
        )

    if min_distance > max_distance:
        raise ValueError(
            "Minimum distance cannot exceed maximum distance."
        )

    if distance <= min_distance:
        return 1.0

    if distance >= max_distance:
        return 0.0

    return 1.0 - (
        (distance - min_distance)
        / (max_distance - min_distance)
    )

def calculate_stereo_pan(
    source_position: tuple[float, float],
    listener_position: tuple[float, float],
) -> float:
    """Calculate stereo pan from source position.

    Returns:
        -1.0 = full left
         0.0 = center
         1.0 = full right
    """

    dx = source_position[0] - listener_position[0]

    if dx == 0.0:
        return 0.0

    distance = calculate_distance(
        source_position,
        listener_position,
    )

    if distance == 0.0:
        return 0.0

    return max(
        -1.0,
        min(
            1.0,
            dx / distance,
        ),
    )

def calculate_pan_gains(
    pan: float,
) -> tuple[float, float]:
    """Calculate stereo gains from a pan value.

    Args:
        pan:
            Stereo position from -1.0 (left)
            to 1.0 (right).

    Returns:
        A tuple containing:
            left_gain
            right_gain
    """

    if not -1.0 <= pan <= 1.0:
        raise ValueError(
            "Pan must be between -1.0 and 1.0."
        )

    left_gain = 1.0 - max(
        0.0,
        pan,
    )

    right_gain = 1.0 + min(
        0.0,
        pan,
    )

    return left_gain, right_gain