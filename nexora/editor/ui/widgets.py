"""Small renderer-backed UI toolkit shared by standalone editors.

This module deliberately does not use Nexora's UINode tree.  Controls use
top-left screen rectangles while the renderer itself remains in centered
coordinates.  That keeps layout math explicit and makes the standalone
editors independent from the regular editor UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


Color = tuple[int, int, int, int]

# Global readability multiplier for the standalone editor UI.  Change this
# value once to adjust all labels, buttons and field text consistently.
UI_SCALE = 1.50


@dataclass(slots=True)
class UITheme:
    background: Color = (17, 19, 23, 255)
    panel: Color = (29, 32, 38, 255)
    panel_dark: Color = (22, 25, 30, 255)
    border: Color = (61, 67, 78, 255)
    input: Color = (35, 39, 47, 255)
    input_focus: Color = (43, 49, 61, 255)
    button: Color = (38, 43, 52, 255)
    button_hover: Color = (52, 61, 76, 255)
    accent: Color = (84, 142, 235, 255)
    text: Color = (235, 237, 242, 255)
    muted: Color = (154, 161, 174, 255)
    warning: Color = (240, 174, 86, 255)
    error: Color = (238, 112, 112, 255)
    selected: Color = (50, 82, 125, 255)


@dataclass(slots=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    def contains(self, x: float, y: float) -> bool:
        return (
            self.x <= float(x) <= self.x + self.width
            and self.y <= float(y) <= self.y + self.height
        )

    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2.0, self.y + self.height / 2.0)


def rgba(color: Color) -> tuple[float, float, float, float]:
    return tuple(channel / 255.0 for channel in color)


def _world_point(x: float, y: float, width: float, height: float) -> tuple[float, float]:
    return (float(x) - width / 2.0, float(y) - height / 2.0)


def draw_rect(renderer, rect: Rect, color: Color, viewport: tuple[float, float], *, radius: float = 0.0) -> None:
    width, height = viewport
    x, y = _world_point(rect.x + rect.width / 2.0, rect.y + rect.height / 2.0, width, height)
    renderer.rect(x, y, rect.width, rect.height, color=rgba(color), radius=radius)


def draw_outline(renderer, rect: Rect, color: Color, viewport: tuple[float, float], *, width: float = 1.0) -> None:
    screen_width, screen_height = viewport
    left, top = _world_point(rect.x, rect.y, screen_width, screen_height)
    right, bottom = _world_point(rect.x + rect.width, rect.y + rect.height, screen_width, screen_height)
    renderer.line(left, top, right, top, width=width, color=rgba(color))
    renderer.line(right, top, right, bottom, width=width, color=rgba(color))
    renderer.line(right, bottom, left, bottom, width=width, color=rgba(color))
    renderer.line(left, bottom, left, top, width=width, color=rgba(color))


def draw_text(
    renderer,
    text: str,
    x: float,
    y: float,
    viewport: tuple[float, float],
    *,
    scale: float = 0.65,
    color: Color = (235, 237, 242, 255),
    align: str = "left",
) -> None:
    if not text:
        return
    scale = float(scale) * UI_SCALE
    width, height = viewport
    lines = str(text).splitlines() or [""]
    text_renderer = getattr(getattr(renderer, "gpu", None), "text_renderer", None)
    previous = None
    if text_renderer is not None:
        previous = text_renderer.color
        text_renderer.set_color(*rgba(color))
    try:
        for index, line in enumerate(lines):
            line_x = float(x)
            if align != "left":
                measured_width, _ = renderer.text_measure(line, scale=scale)
                if align == "center":
                    line_x -= measured_width / 2.0
                elif align == "right":
                    line_x -= measured_width
            world_x, world_y = _world_point(line_x, y, width, height)
            renderer.text(line, world_x, world_y + renderer.text_baseline(scale=scale), scale=scale)
            y += renderer.text_measure("Ag", scale=scale)[1]
    finally:
        if text_renderer is not None and previous is not None:
            text_renderer.set_color(*previous)


class Control:
    def __init__(self, rect: Rect) -> None:
        self.rect = rect
        self.visible = True
        self.enabled = True
        self.hovered = False

    def update(self, input_manager, mouse_x: float, mouse_y: float) -> bool:
        self.hovered = self.visible and self.rect.contains(mouse_x, mouse_y)
        return False

    def render(self, renderer, viewport: tuple[float, float], theme: UITheme) -> None:
        del renderer, viewport, theme


class Button(Control):
    def __init__(self, rect: Rect, text: str, on_click: Callable[[], None] | None = None) -> None:
        super().__init__(rect)
        self.text = str(text)
        self.on_click = on_click
        self.pressed = False
        self.selected = False
        self.text_scale = 0.62

    def update(self, input_manager, mouse_x: float, mouse_y: float) -> bool:
        super().update(input_manager, mouse_x, mouse_y)
        self.pressed = bool(self.hovered and input_manager.mouse_down("left"))
        if self.enabled and self.hovered and input_manager.mouse_pressed("left"):
            if self.on_click is not None:
                self.on_click()
            return True
        return False

    def render(self, renderer, viewport, theme: UITheme) -> None:
        if not self.visible:
            return
        color = theme.selected if self.selected else (theme.button_hover if self.hovered else theme.button)
        if not self.enabled:
            color = theme.panel_dark
        draw_rect(renderer, self.rect, color, viewport, radius=4.0)
        draw_outline(renderer, self.rect, theme.accent if self.pressed else theme.border, viewport)
        text_height = renderer.text_measure("Ag", scale=self.text_scale * UI_SCALE)[1]
        draw_text(
            renderer,
            self.text,
            self.rect.x + self.rect.width / 2.0,
            self.rect.y + (self.rect.height - text_height) / 2.0,
            viewport,
            scale=self.text_scale,
            color=theme.text if self.enabled else theme.muted,
            align="center",
        )


class Menu(Control):
    """Compact top-bar menu with a renderer-backed drop-down list."""

    def __init__(self, rect: Rect, title: str, items: list[tuple[str, Callable[[], None]]]) -> None:
        super().__init__(rect)
        self.title = str(title)
        self.items = [(str(label), callback) for label, callback in items]
        self.open = False
        self.item_height = 30.0
        self.menu_width = 220.0
        self.popup_origin: tuple[float, float] | None = None
        self.on_open: Callable[["Menu"], None] | None = None
        self._last_mouse = (-1.0, -1.0)

    @property
    def dropdown_rect(self) -> Rect:
        x, y = self.popup_origin or (self.rect.x, self.rect.y + self.rect.height)
        return Rect(x, y, self.menu_width, self.item_height * len(self.items))

    def update(self, input_manager, mouse_x: float, mouse_y: float) -> bool:
        self._last_mouse = (float(mouse_x), float(mouse_y))
        self.hovered = self.visible and self.rect.contains(mouse_x, mouse_y)
        if not self.visible or not input_manager.mouse_pressed("left"):
            return False
        if self.rect.contains(mouse_x, mouse_y):
            self.open = not self.open
            if self.open and self.on_open is not None:
                self.on_open(self)
            return True
        if self.open:
            dropdown = self.dropdown_rect
            if dropdown.contains(mouse_x, mouse_y):
                index = int((mouse_y - dropdown.y) // self.item_height)
                if 0 <= index < len(self.items):
                    _label, callback = self.items[index]
                    self.open = False
                    callback()
                    return True
            self.open = False
            return True
        return False

    def render(self, renderer, viewport, theme: UITheme) -> None:
        if not self.visible:
            return
        draw_rect(renderer, self.rect, theme.button_hover if self.hovered or self.open else theme.button, viewport, radius=4.0)
        draw_outline(renderer, self.rect, theme.accent if self.open else theme.border, viewport)
        text_height = renderer.text_measure("Ag", scale=0.64 * UI_SCALE)[1]
        draw_text(renderer, self.title, self.rect.x + self.rect.width / 2.0, self.rect.y + (self.rect.height - text_height) / 2.0, viewport, scale=0.64, align="center")
        if not self.open:
            return
        dropdown = self.dropdown_rect
        draw_rect(renderer, dropdown, theme.panel, viewport, radius=3.0)
        draw_outline(renderer, dropdown, theme.accent, viewport)
        for index, (label, _callback) in enumerate(self.items):
            item = Rect(dropdown.x + 2.0, dropdown.y + index * self.item_height + 2.0, dropdown.width - 4.0, self.item_height - 4.0)
            if item.contains(*self._last_mouse):
                draw_rect(renderer, item, theme.selected, viewport, radius=2.0)
            text_height = renderer.text_measure("Ag", scale=0.58 * UI_SCALE)[1]
            draw_text(renderer, label, item.x + 10.0, item.y + (item.height - text_height) / 2.0, viewport, scale=0.58)

class TextField(Control):
    def __init__(self, rect: Rect, text: str = "", placeholder: str = "") -> None:
        super().__init__(rect)
        self.text = str(text)
        self.placeholder = str(placeholder)
        self.focused = False
        self.caret = len(self.text)
        self.on_submit: Callable[[str], None] | None = None
        self.on_change: Callable[[str], None] | None = None
        self.text_scale = 0.62

    def set_text(self, text: str) -> None:
        self.text = str(text)
        self.caret = min(self.caret, len(self.text))

    def focus(self, input_manager) -> None:
        self.focused = True
        try:
            input_manager.acquire_text_input(self)
        except Exception:
            pass

    def blur(self, input_manager) -> None:
        if not self.focused:
            return
        self.focused = False
        try:
            input_manager.release_text_input(self)
        except Exception:
            pass

    def _changed(self, value: str) -> None:
        self.text = value
        self.caret = max(0, min(self.caret, len(self.text)))
        if self.on_change is not None:
            self.on_change(self.text)

    def update(self, input_manager, mouse_x: float, mouse_y: float) -> bool:
        super().update(input_manager, mouse_x, mouse_y)
        if self.enabled and self.hovered and input_manager.mouse_pressed("left"):
            self.focus(input_manager)
            self.caret = len(self.text)
            return True
        if not self.focused:
            return False
        for value in input_manager.text_input:
            self._changed(self.text[: self.caret] + str(value) + self.text[self.caret :])
            self.caret += len(str(value))
        if input_manager.key_pressed("backspace") and self.caret > 0:
            self._changed(self.text[: self.caret - 1] + self.text[self.caret :])
            self.caret -= 1
        if input_manager.key_pressed("delete") and self.caret < len(self.text):
            self._changed(self.text[: self.caret] + self.text[self.caret + 1 :])
        if input_manager.key_pressed("left"):
            self.caret = max(0, self.caret - 1)
        if input_manager.key_pressed("right"):
            self.caret = min(len(self.text), self.caret + 1)
        if input_manager.key_pressed("home"):
            self.caret = 0
        if input_manager.key_pressed("end"):
            self.caret = len(self.text)
        if input_manager.key_pressed("return") and self.on_submit is not None:
            self.on_submit(self.text)
        return False

    def render(self, renderer, viewport, theme: UITheme) -> None:
        if not self.visible:
            return
        draw_rect(renderer, self.rect, theme.input_focus if self.focused else theme.input, viewport, radius=4.0)
        draw_outline(renderer, self.rect, theme.accent if self.focused else theme.border, viewport, width=2.0 if self.focused else 1.0)
        value = self.text or self.placeholder
        color = theme.text if self.text else theme.muted
        draw_text(renderer, value, self.rect.x + 9.0, self.rect.y + 7.0, viewport, scale=self.text_scale, color=color)
        if self.focused:
            prefix = self.text[: self.caret]
            prefix_width, _ = renderer.text_measure(prefix, scale=self.text_scale * UI_SCALE)
            width, height = viewport
            x, y = _world_point(self.rect.x + 9.0 + prefix_width, self.rect.y + 6.0, width, height)
            renderer.line(x, y, x, y + self.rect.height - 12.0, width=1.0, color=rgba(theme.text))


class CheckBox(Control):
    def __init__(self, rect: Rect, text: str, checked: bool = False, on_change: Callable[[bool], None] | None = None) -> None:
        super().__init__(rect)
        self.text = str(text)
        self.checked = bool(checked)
        self.on_change = on_change

    def update(self, input_manager, mouse_x: float, mouse_y: float) -> bool:
        super().update(input_manager, mouse_x, mouse_y)
        if self.enabled and self.hovered and input_manager.mouse_pressed("left"):
            self.checked = not self.checked
            if self.on_change is not None:
                self.on_change(self.checked)
            return True
        return False

    def render(self, renderer, viewport, theme: UITheme) -> None:
        if not self.visible:
            return
        box = Rect(self.rect.x, self.rect.y + 2.0, 20.0, 20.0)
        draw_rect(renderer, box, theme.accent if self.checked else theme.input, viewport, radius=3.0)
        draw_outline(renderer, box, theme.border, viewport)
        if self.checked:
            draw_text(renderer, "✓", box.x + 3.0, box.y - 1.0, viewport, scale=0.65, color=theme.text)
        draw_text(renderer, self.text, self.rect.x + 28.0, self.rect.y + 2.0, viewport, scale=0.60, color=theme.text)


class Dropdown(Control):
    def __init__(self, rect: Rect, options: tuple[str, ...] | list[str], selected: int = 0, on_change: Callable[[int, str], None] | None = None) -> None:
        super().__init__(rect)
        self.options = tuple(str(option) for option in options)
        self.selected = max(0, min(int(selected), len(self.options) - 1)) if self.options else -1
        self.on_change = on_change

    @property
    def value(self) -> str:
        return self.options[self.selected] if 0 <= self.selected < len(self.options) else ""

    def update(self, input_manager, mouse_x: float, mouse_y: float) -> bool:
        super().update(input_manager, mouse_x, mouse_y)
        if self.enabled and self.hovered and input_manager.mouse_pressed("left") and self.options:
            self.selected = (self.selected + 1) % len(self.options)
            if self.on_change is not None:
                self.on_change(self.selected, self.value)
            return True
        return False

    def render(self, renderer, viewport, theme: UITheme) -> None:
        if not self.visible:
            return
        draw_rect(renderer, self.rect, theme.input, viewport, radius=4.0)
        draw_outline(renderer, self.rect, theme.accent if self.hovered else theme.border, viewport)
        draw_text(renderer, self.value, self.rect.x + 9.0, self.rect.y + 7.0, viewport, scale=0.60, color=theme.text)
        draw_text(renderer, "▾", self.rect.x + self.rect.width - 20.0, self.rect.y + 7.0, viewport, scale=0.60, color=theme.muted)


class ListBox(Control):
    def __init__(self, rect: Rect, on_change: Callable[[int], None] | None = None) -> None:
        super().__init__(rect)
        self.items: list[str] = []
        self.selected = -1
        self.on_change = on_change
        self.row_height = 30.0
        self.scroll = 0
        self.row_action: Callable[[int], None] | None = None
        self.row_action_state: Callable[[int], bool] | None = None
        self.row_action_width = 34.0
        self.scrollbar_width = 12.0

    def set_items(self, items: list[str] | tuple[str, ...]) -> None:
        self.items = [str(item) for item in items]
        self.selected = min(self.selected, len(self.items) - 1)
        visible_rows = max(1, int(self.rect.height // self.row_height))
        self.scroll = min(self.scroll, max(0, len(self.items) - visible_rows))

    def update(self, input_manager, mouse_x: float, mouse_y: float) -> bool:
        super().update(input_manager, mouse_x, mouse_y)
        if not self.hovered:
            return False
        visible_rows = max(1, int(self.rect.height // self.row_height))
        max_scroll = max(0, len(self.items) - visible_rows)
        _wheel_x, wheel_y = input_manager.wheel
        if wheel_y:
            self.scroll = max(0, min(max_scroll, self.scroll - int(wheel_y)))
            return True
        if input_manager.mouse_pressed("left"):
            if max_scroll and mouse_x >= self.rect.x + self.rect.width - self.scrollbar_width:
                fraction = (mouse_y - self.rect.y) / max(1.0, self.rect.height)
                self.scroll = max(0, min(max_scroll, int(fraction * max_scroll)))
                return True
            index = int((mouse_y - self.rect.y) // self.row_height) + self.scroll
            if 0 <= index < len(self.items):
                if self.row_action is not None and mouse_x >= self.rect.x + self.rect.width - self.row_action_width:
                    self.row_action(index)
                    return True
                self.selected = index
                if self.on_change is not None:
                    self.on_change(index)
                return True
        return False

    def render(self, renderer, viewport, theme: UITheme) -> None:
        if not self.visible:
            return
        draw_rect(renderer, self.rect, theme.panel_dark, viewport)
        draw_outline(renderer, self.rect, theme.border, viewport)
        visible_rows = max(1, int(self.rect.height // self.row_height))
        max_scroll = max(0, len(self.items) - visible_rows)
        for row in range(visible_rows):
            index = row + self.scroll
            if index >= len(self.items):
                break
            row_rect = Rect(self.rect.x + 3.0, self.rect.y + row * self.row_height + 3.0, self.rect.width - 6.0, self.row_height - 3.0)
            if index == self.selected:
                draw_rect(renderer, row_rect, theme.selected, viewport, radius=3.0)
            text_width = row_rect.width - self.scrollbar_width - (self.row_action_width if self.row_action is not None else 0.0)
            draw_text(renderer, self.items[index], row_rect.x + 8.0, row_rect.y + 7.0, viewport, scale=0.58, color=theme.text)
            if self.row_action is not None:
                symbol = "◉" if self.row_action_state is None or self.row_action_state(index) else "○"
                draw_text(renderer, symbol, row_rect.x + text_width + self.row_action_width / 2.0, row_rect.y + 5.0, viewport, scale=0.70, color=theme.accent if symbol == "◉" else theme.muted, align="center")
        if max_scroll:
            track = Rect(self.rect.x + self.rect.width - self.scrollbar_width + 2.0, self.rect.y + 3.0, self.scrollbar_width - 5.0, self.rect.height - 6.0)
            draw_rect(renderer, track, theme.input, viewport, radius=3.0)
            thumb_height = max(22.0, track.height * visible_rows / max(visible_rows, len(self.items)))
            thumb_y = track.y + (track.height - thumb_height) * (self.scroll / max_scroll)
            draw_rect(renderer, Rect(track.x, thumb_y, track.width, thumb_height), theme.accent, viewport, radius=3.0)


class CategorizedListBox(Control):
    """Scrollable list with collapsible category headers."""

    def __init__(self, rect: Rect, on_change: Callable[[int], None] | None = None) -> None:
        super().__init__(rect)
        self.groups: list[tuple[str, list[tuple[str, int]]]] = []
        self.rows: list[tuple[str, str, int | None]] = []
        self.collapsed: set[str] = set()
        self.selected_asset = -1
        self.on_change = on_change
        self.row_height = 30.0
        self.scroll = 0
        self.scrollbar_width = 12.0

    def set_groups(self, groups: dict[str, list[tuple[str, int]]]) -> None:
        self.collapsed.intersection_update(groups)
        self.groups = [(name, list(groups[name])) for name in groups]
        self._rebuild_rows()
        if self.selected_asset not in {
            asset_index
            for _category, items in self.groups
            for _label, asset_index in items
        }:
            self.selected_asset = -1

    def _rebuild_rows(self) -> None:
        self.rows = []
        for category, items in self.groups:
            self.rows.append(("category", category, None))
            if category not in self.collapsed:
                self.rows.extend(("item", label, asset_index) for label, asset_index in items)
        visible_rows = max(1, int(self.rect.height // self.row_height))
        self.scroll = min(self.scroll, max(0, len(self.rows) - visible_rows))

    def update(self, input_manager, mouse_x: float, mouse_y: float) -> bool:
        super().update(input_manager, mouse_x, mouse_y)
        if not self.hovered:
            return False
        visible_rows = max(1, int(self.rect.height // self.row_height))
        max_scroll = max(0, len(self.rows) - visible_rows)
        _wheel_x, wheel_y = input_manager.wheel
        if wheel_y:
            self.scroll = max(0, min(max_scroll, self.scroll - int(wheel_y)))
            return True
        if not input_manager.mouse_pressed("left"):
            return False
        if max_scroll and mouse_x >= self.rect.x + self.rect.width - self.scrollbar_width:
            fraction = (mouse_y - self.rect.y) / max(1.0, self.rect.height)
            self.scroll = max(0, min(max_scroll, int(fraction * max_scroll)))
            return True
        row_index = int((mouse_y - self.rect.y) // self.row_height) + self.scroll
        if not 0 <= row_index < len(self.rows):
            return True
        row_type, label, asset_index = self.rows[row_index]
        if row_type == "category":
            if label in self.collapsed:
                self.collapsed.remove(label)
            else:
                self.collapsed.add(label)
            self._rebuild_rows()
            return True
        if asset_index is not None:
            self.selected_asset = asset_index
            if self.on_change is not None:
                self.on_change(asset_index)
        return True

    def render(self, renderer, viewport, theme: UITheme) -> None:
        if not self.visible:
            return
        draw_rect(renderer, self.rect, theme.panel_dark, viewport)
        draw_outline(renderer, self.rect, theme.border, viewport)
        visible_rows = max(1, int(self.rect.height // self.row_height))
        max_scroll = max(0, len(self.rows) - visible_rows)
        category_counts = {name: len(items) for name, items in self.groups}
        for row in range(visible_rows):
            index = row + self.scroll
            if index >= len(self.rows):
                break
            row_type, label, asset_index = self.rows[index]
            row_rect = Rect(self.rect.x + 3.0, self.rect.y + row * self.row_height + 3.0, self.rect.width - 6.0, self.row_height - 3.0)
            if row_type == "category":
                draw_rect(renderer, row_rect, theme.button, viewport, radius=3.0)
                symbol = "▸" if label in self.collapsed else "▾"
                draw_text(renderer, f"{symbol}  {label} ({category_counts.get(label, 0)})", row_rect.x + 8.0, row_rect.y + 7.0, viewport, scale=0.56, color=theme.text)
            else:
                if asset_index == self.selected_asset:
                    draw_rect(renderer, row_rect, theme.selected, viewport, radius=3.0)
                draw_text(renderer, label, row_rect.x + 24.0, row_rect.y + 7.0, viewport, scale=0.54, color=theme.text)
        if max_scroll:
            track = Rect(self.rect.x + self.rect.width - self.scrollbar_width + 2.0, self.rect.y + 3.0, self.scrollbar_width - 5.0, self.rect.height - 6.0)
            draw_rect(renderer, track, theme.input, viewport, radius=3.0)
            thumb_height = max(22.0, track.height * visible_rows / max(visible_rows, len(self.rows)))
            thumb_y = track.y + (track.height - thumb_height) * (self.scroll / max_scroll)
            draw_rect(renderer, Rect(track.x, thumb_y, track.width, thumb_height), theme.accent, viewport, radius=3.0)
