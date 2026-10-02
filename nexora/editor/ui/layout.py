"""Small layout helpers shared by standalone editor screens."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .widgets import Rect


@dataclass(frozen=True, slots=True)
class FormLayout:
    """Reusable geometry for label/control forms.

    Coordinates are expressed in the standalone editor UI coordinate system.
    A row points at the label baseline; controls are placed ``label_gap``
    pixels below it.  ``span`` lets a field consume multiple columns without
    every editor having to repeat the same width arithmetic.
    """

    x: float
    y: float
    width: float
    columns: int = 2
    column_gap: float = 10.0
    row_step: float = 52.0
    control_height: float = 34.0
    label_gap: float = 18.0

    def __post_init__(self) -> None:
        if self.columns <= 0:
            raise ValueError("columns must be greater than zero")
        if self.width < 0.0:
            raise ValueError("width must not be negative")

    @property
    def column_width(self) -> float:
        gaps = self.column_gap * max(0, self.columns - 1)
        return max(0.0, (self.width - gaps) / self.columns)

    def column_x(self, column: int) -> float:
        if not 0 <= column < self.columns:
            raise IndexError("form column out of range")
        return self.x + column * (self.column_width + self.column_gap)

    def span_width(self, span: int = 1) -> float:
        if not 1 <= span <= self.columns:
            raise ValueError("span must fit inside the form columns")
        return self.column_width * span + self.column_gap * (span - 1)

    def label_position(
        self,
        row: float,
        column: int = 0,
        *,
        y_offset: float = 0.0,
    ) -> tuple[float, float]:
        return (
            self.column_x(column),
            self.y + row * self.row_step + y_offset,
        )

    def control_rect(
        self,
        row: float,
        column: int = 0,
        *,
        span: int = 1,
        y_offset: float = 0.0,
        height: float | None = None,
    ) -> Rect:
        if column + span > self.columns:
            raise ValueError("column + span exceeds form width")
        x, label_y = self.label_position(row, column, y_offset=y_offset)
        return Rect(
            x,
            label_y + self.label_gap,
            self.span_width(span),
            self.control_height if height is None else float(height),
        )


def centered_rect(viewport: tuple[float, float], width: float, height: float) -> Rect:
    screen_width, screen_height = viewport
    return Rect(
        float(screen_width) / 2.0 - float(width) / 2.0,
        float(screen_height) / 2.0 - float(height) / 2.0,
        float(width),
        float(height),
    )


def layout_fixed_row(
    controls: Sequence[object],
    widths: Sequence[float],
    *,
    x: float,
    y: float,
    height: float,
    gap: float | Sequence[float] = 6.0,
) -> None:
    """Assign consecutive rectangles with caller supplied widths and gaps."""

    if len(controls) != len(widths):
        raise ValueError("controls and widths must have the same length")
    if isinstance(gap, Sequence) and not isinstance(gap, (str, bytes)):
        gaps = tuple(float(value) for value in gap)
        if len(gaps) != max(0, len(controls) - 1):
            raise ValueError("gap sequence must contain one value between controls")
    else:
        gaps = (float(gap),) * max(0, len(controls) - 1)

    current_x = float(x)
    for index, (control, width) in enumerate(zip(controls, widths, strict=True)):
        control.rect = Rect(current_x, float(y), float(width), float(height))
        if index < len(gaps):
            current_x += float(width) + gaps[index]


def layout_equal_row(
    controls: Sequence[object],
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    gap: float = 6.0,
) -> None:
    """Assign a row of equally sized controls inside ``width``."""

    count = len(controls)
    if count == 0:
        return
    control_width = max(0.0, (float(width) - float(gap) * (count - 1)) / count)
    layout_fixed_row(
        controls,
        (control_width,) * count,
        x=x,
        y=y,
        height=height,
        gap=gap,
    )


def close_other_menus(menus: Iterable[object], active: object) -> None:
    """Close every menu except the one that was just opened."""

    for menu in menus:
        if menu is not active:
            menu.open = False
