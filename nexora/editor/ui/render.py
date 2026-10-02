"""Shared rendering helpers for standalone editor chrome and forms."""

from __future__ import annotations

from collections.abc import Sequence

from .widgets import Color, Rect, UITheme, draw_outline, draw_rect, draw_text


def render_editor_shell(
    renderer,
    viewport: tuple[float, float],
    theme: UITheme,
    *,
    toolbar_height: float,
    status_height: float,
    panels: Sequence[tuple[Rect, Color]] = (),
    outline_rects: Sequence[Rect] = (),
) -> None:
    """Draw the common standalone-editor toolbar, panels and status bar."""

    width, height = viewport
    toolbar = Rect(0.0, 0.0, width, float(toolbar_height))
    status = Rect(
        0.0,
        height - float(status_height),
        width,
        float(status_height),
    )

    draw_rect(renderer, toolbar, theme.panel, viewport)
    for rect, color in panels:
        draw_rect(renderer, rect, color, viewport)
    draw_rect(renderer, status, theme.panel, viewport)

    for rect in (toolbar, *outline_rects):
        draw_outline(renderer, rect, theme.border, viewport)


def render_document_title(
    renderer,
    viewport: tuple[float, float],
    theme: UITheme,
    title: str,
    *,
    dirty: bool = False,
    x_offset: float = 16.0,
    y: float = 18.0,
    scale: float = 0.62,
) -> None:
    """Render the current document name at the right side of the toolbar."""

    width, _height = viewport
    suffix = " *" if dirty else ""
    draw_text(
        renderer,
        f"{title}{suffix}",
        width - float(x_offset),
        float(y),
        viewport,
        scale=scale,
        color=theme.muted,
        align="right",
    )


def render_status_bar(
    renderer,
    viewport: tuple[float, float],
    theme: UITheme,
    status: str,
    editor_name: str,
    *,
    status_height: float,
    y_offset: float = 7.0,
    scale: float = 0.56,
) -> None:
    """Render status text on the left and editor identity on the right."""

    width, height = viewport
    y = height - float(status_height) + float(y_offset)
    draw_text(
        renderer,
        status,
        12.0,
        y,
        viewport,
        scale=scale,
        color=theme.muted,
    )
    draw_text(
        renderer,
        editor_name,
        width - 12.0,
        y,
        viewport,
        scale=scale,
        color=theme.muted,
        align="right",
    )


def render_section_title(
    renderer,
    viewport: tuple[float, float],
    theme: UITheme,
    rect: Rect,
    title: str,
    *,
    x_offset: float = 12.0,
    y_offset: float = 14.0,
    scale: float = 0.76,
) -> None:
    """Render a title relative to a panel or viewport rectangle."""

    draw_text(
        renderer,
        title,
        rect.x + float(x_offset),
        rect.y + float(y_offset),
        viewport,
        scale=scale,
        color=theme.text,
    )


def render_form_label(
    renderer,
    viewport: tuple[float, float],
    theme: UITheme,
    text: str,
    x: float,
    y: float,
    *,
    scale: float = 0.44,
) -> None:
    """Render the muted label style used above standalone-editor controls."""

    draw_text(
        renderer,
        text,
        float(x),
        float(y),
        viewport,
        scale=scale,
        color=theme.muted,
    )


__all__ = [
    "render_document_title",
    "render_editor_shell",
    "render_form_label",
    "render_section_title",
    "render_status_bar",
]
