from __future__ import annotations


def lerp_value(
    a: float,
    b: float,
    t: float,
) -> float:
    """Linearly interpolate between two numeric values."""
    return a + (b - a) * t
