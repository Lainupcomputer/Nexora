"""Shared modal dialog rendering for standalone Nexora editors.

The standalone editors keep their domain-specific callbacks, while this module
owns the common browser/info geometry and drawing.  That keeps dialogs visually
consistent and prevents every editor from carrying its own copy of the same
layout code.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .layout import centered_rect
from .widgets import Rect, UITheme, draw_outline, draw_rect, draw_text


def browser_window(
    viewport: tuple[float, float],
    *,
    margin_x: float = 150.0,
    margin_y: float = 76.0,
) -> Rect:
    width, height = viewport
    return Rect(
        margin_x,
        margin_y,
        max(320.0, width - margin_x * 2.0),
        max(220.0, height - margin_y * 2.0),
    )


def render_file_browser_dialog(
    renderer,
    viewport: tuple[float, float],
    theme: UITheme,
    *,
    title: str,
    path: str | Path,
    list_box,
    cancel_button,
    name_field=None,
    action_button=None,
    show_filename: bool = False,
    margin_x: float = 150.0,
    margin_y: float = 76.0,
) -> Rect:
    """Layout and render the shared project file-browser modal."""

    width, height = viewport
    draw_rect(renderer, Rect(0, 0, width, height), (0, 0, 0, 175), viewport)
    window = browser_window(viewport, margin_x=margin_x, margin_y=margin_y)
    draw_rect(renderer, window, theme.panel, viewport, radius=6.0)
    draw_outline(renderer, window, theme.border, viewport)

    draw_text(renderer, title, window.x + 18.0, window.y + 16.0, viewport, scale=0.80)
    draw_text(
        renderer,
        str(path),
        window.x + 18.0,
        window.y + 50.0,
        viewport,
        scale=0.48,
        color=theme.muted,
    )

    footer_y = window.y + window.height - 50.0
    list_bottom = window.y + window.height - (150.0 if show_filename else 72.0)
    list_box.rect = Rect(
        window.x + 18.0,
        window.y + 78.0,
        max(220.0, window.width - 36.0),
        max(100.0, list_bottom - (window.y + 78.0)),
    )

    button_width = 108.0
    button_height = 32.0
    cancel_x = window.x + window.width - 18.0 - button_width
    if show_filename and action_button is not None:
        action_button.rect = Rect(cancel_x, footer_y, button_width, button_height)
        cancel_x -= button_width + 10.0
    cancel_button.rect = Rect(cancel_x, footer_y, button_width, button_height)

    if show_filename and name_field is not None:
        draw_text(
            renderer,
            "File name",
            window.x + 18.0,
            window.y + window.height - 72.0,
            viewport,
            scale=0.48,
            color=theme.muted,
        )
        name_field.rect = Rect(
            window.x + 18.0,
            footer_y,
            max(180.0, cancel_x - (window.x + 18.0) - 14.0),
            button_height,
        )

    list_box.render(renderer, viewport, theme)
    cancel_button.render(renderer, viewport, theme)
    if show_filename and name_field is not None:
        name_field.render(renderer, viewport, theme)
    if show_filename and action_button is not None:
        action_button.render(renderer, viewport, theme)

    return window


def render_info_dialog(
    renderer,
    viewport: tuple[float, float],
    theme: UITheme,
    *,
    title: str,
    lines: Sequence[str],
    close_button,
    width: float = 660.0,
    height: float = 340.0,
    line_step: float = 38.0,
) -> Rect:
    """Layout and render a standard informational modal."""

    screen_width, screen_height = viewport
    draw_rect(renderer, Rect(0, 0, screen_width, screen_height), (0, 0, 0, 175), viewport)
    window = centered_rect(viewport, width, height)
    draw_rect(renderer, window, theme.panel, viewport, radius=6.0)
    draw_outline(renderer, window, theme.border, viewport)
    draw_text(renderer, title, window.x + 22.0, window.y + 20.0, viewport, scale=0.86)

    y = window.y + 78.0
    for line in lines:
        draw_text(renderer, str(line), window.x + 24.0, y, viewport, scale=0.60, color=theme.text)
        y += line_step

    close_button.rect = Rect(
        window.x + window.width - 126.0,
        window.y + window.height - 52.0,
        108.0,
        32.0,
    )
    close_button.render(renderer, viewport, theme)
    return window


__all__ = [
    "browser_window",
    "render_file_browser_dialog",
    "render_info_dialog",
]
