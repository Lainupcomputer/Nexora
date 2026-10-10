from __future__ import annotations

import math
from collections.abc import Callable


EaseFunction = Callable[[float], float]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def linear(t: float) -> float:
    return _clamp01(t)


def quad_in(t: float) -> float:
    t = _clamp01(t)
    return t * t


def quad_out(t: float) -> float:
    t = _clamp01(t)
    return 1.0 - (1.0 - t) * (1.0 - t)


def quad_in_out(t: float) -> float:
    t = _clamp01(t)
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0


def cubic_in(t: float) -> float:
    t = _clamp01(t)
    return t * t * t


def cubic_out(t: float) -> float:
    t = _clamp01(t)
    return 1.0 - (1.0 - t) ** 3


def cubic_in_out(t: float) -> float:
    t = _clamp01(t)
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


def sine_in(t: float) -> float:
    t = _clamp01(t)
    return 1.0 - math.cos((t * math.pi) / 2.0)


def sine_out(t: float) -> float:
    t = _clamp01(t)
    return math.sin((t * math.pi) / 2.0)


def sine_in_out(t: float) -> float:
    t = _clamp01(t)
    return -(math.cos(math.pi * t) - 1.0) / 2.0


def expo_in(t: float) -> float:
    t = _clamp01(t)
    if t == 0.0:
        return 0.0
    return 2.0 ** (10.0 * t - 10.0)


def expo_out(t: float) -> float:
    t = _clamp01(t)
    if t == 1.0:
        return 1.0
    return 1.0 - 2.0 ** (-10.0 * t)


def expo_in_out(t: float) -> float:
    t = _clamp01(t)
    if t == 0.0:
        return 0.0
    if t == 1.0:
        return 1.0
    if t < 0.5:
        return (2.0 ** (20.0 * t - 10.0)) / 2.0
    return (2.0 - 2.0 ** (-20.0 * t + 10.0)) / 2.0


def back_in(t: float) -> float:
    t = _clamp01(t)
    c1 = 1.70158
    c3 = c1 + 1.0
    return c3 * t * t * t - c1 * t * t


def back_out(t: float) -> float:
    t = _clamp01(t)
    c1 = 1.70158
    c3 = c1 + 1.0
    x = t - 1.0
    return 1.0 + c3 * x * x * x + c1 * x * x


def back_in_out(t: float) -> float:
    t = _clamp01(t)
    c1 = 1.70158
    c2 = c1 * 1.525
    if t < 0.5:
        x = 2.0 * t
        return (x * x * ((c2 + 1.0) * x - c2)) / 2.0
    x = 2.0 * t - 2.0
    return (x * x * ((c2 + 1.0) * x + c2) + 2.0) / 2.0


def bounce_out(t: float) -> float:
    t = _clamp01(t)
    n1 = 7.5625
    d1 = 2.75

    if t < 1.0 / d1:
        return n1 * t * t
    if t < 2.0 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375

    t -= 2.625 / d1
    return n1 * t * t + 0.984375


def bounce_in(t: float) -> float:
    return 1.0 - bounce_out(1.0 - _clamp01(t))


def bounce_in_out(t: float) -> float:
    t = _clamp01(t)
    if t < 0.5:
        return (1.0 - bounce_out(1.0 - 2.0 * t)) / 2.0
    return (1.0 + bounce_out(2.0 * t - 1.0)) / 2.0


EASINGS: dict[str, EaseFunction] = {
    "linear": linear,
    "quad_in": quad_in,
    "quad_out": quad_out,
    "quad_in_out": quad_in_out,
    "cubic_in": cubic_in,
    "cubic_out": cubic_out,
    "cubic_in_out": cubic_in_out,
    "sine_in": sine_in,
    "sine_out": sine_out,
    "sine_in_out": sine_in_out,
    "expo_in": expo_in,
    "expo_out": expo_out,
    "expo_in_out": expo_in_out,
    "back_in": back_in,
    "back_out": back_out,
    "back_in_out": back_in_out,
    "bounce_in": bounce_in,
    "bounce_out": bounce_out,
    "bounce_in_out": bounce_in_out,
}


def resolve_easing(easing: str | EaseFunction) -> EaseFunction:
    if callable(easing):
        return easing

    name = str(easing).strip().lower()
    try:
        return EASINGS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown easing: {easing}") from exc
