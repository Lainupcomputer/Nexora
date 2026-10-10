from __future__ import annotations

from typing import Callable


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def ease_linear(t: float) -> float:
    return t


def ease_in(t: float) -> float:
    return t * t


def ease_out(t: float) -> float:
    inverse = 1.0 - t
    return 1.0 - inverse * inverse


def ease_in_out(t: float) -> float:
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0


EASING_FUNCTIONS: dict[str, Callable[[float], float]] = {
    "linear": ease_linear,
    "ease_in": ease_in,
    "ease_out": ease_out,
    "ease_in_out": ease_in_out,
}


def ease_value(progress: float, easing: str) -> float:
    progress = clamp01(progress)
    try:
        fn = EASING_FUNCTIONS[easing]
    except KeyError as exc:
        raise ValueError(f"Unknown easing: {easing!r}") from exc
    return fn(progress)
