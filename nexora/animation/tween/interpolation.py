from __future__ import annotations

from numbers import Real


def interpolate(start, end, t: float):
    t = float(t)

    if isinstance(start, Real) and isinstance(end, Real):
        return float(start) + (float(end) - float(start)) * t

    if isinstance(start, tuple) and isinstance(end, tuple):
        if len(start) != len(end):
            raise ValueError("Tween tuples must have the same length.")
        return tuple(interpolate(a, b, t) for a, b in zip(start, end))

    if isinstance(start, list) and isinstance(end, list):
        if len(start) != len(end):
            raise ValueError("Tween lists must have the same length.")
        return [interpolate(a, b, t) for a, b in zip(start, end)]

    raise TypeError(
        "Tween values must be numeric values, tuples, or lists of numeric values."
    )
