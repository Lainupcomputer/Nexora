"""Small layout helpers shared by standalone editor screens."""

from __future__ import annotations

from collections.abc import Iterable

from .widgets import Rect


def centered_rect(viewport: tuple[float, float], width: float, height: float) -> Rect:
    screen_width, screen_height = viewport
    return Rect(
        float(screen_width) / 2.0 - float(width) / 2.0,
        float(screen_height) / 2.0 - float(height) / 2.0,
        float(width),
        float(height),
    )


def close_other_menus(menus: Iterable[object], active: object) -> None:
    """Close every menu except the one that was just opened."""

    for menu in menus:
        if menu is not active:
            menu.open = False
