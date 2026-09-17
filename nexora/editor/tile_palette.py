from __future__ import annotations

from collections.abc import Callable

from nexora.nodes.ui.containers.panel import Panel


class TilePalette(Panel):
    """Compact visual palette for the tiles of one TileSet."""

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)
        self.tileset = None
        self.texture = None
        self.selected_index = -1
        self.hovered_index = -1
        self.cell_size = 58.0
        self.padding = 8.0
        self.scroll_row = 0
        self.on_change: Callable[[int, str], None] | None = None
        self.background = (20, 22, 25, 255)
        self.border_color = (60, 64, 70, 255)
        self.border_width = 1.0
        self.border_radius = 4.0

    def set_tileset(self, tileset, texture=None) -> None:
        changed = tileset is not self.tileset or texture is not self.texture
        self.tileset = tileset
        self.texture = texture
        if changed:
            self.scroll_row = 0
            self.hovered_index = -1
            if tileset is None or tileset.tile_count <= 0:
                self.selected_index = -1
            elif not tileset.contains(self.selected_index):
                self.selected_index = 0

    def set_selected_index(self, index: int, *, emit: bool = False) -> None:
        if self.tileset is None or self.tileset.tile_count <= 0:
            self.selected_index = -1
            return
        index = max(0, min(int(index), self.tileset.tile_count - 1))
        changed = index != self.selected_index
        self.selected_index = index
        if emit and changed and self.on_change is not None:
            self.on_change(index, f"Tile {index}")

    def _grid_metrics(self) -> tuple[int, int, float, float]:
        width, height = self.size
        columns = max(
            1,
            int(max(1.0, width - self.padding * 2.0) // self.cell_size),
        )
        rows = 1
        if self.tileset is not None and self.tileset.tile_count:
            rows = (self.tileset.tile_count + columns - 1) // columns
        visible_rows = max(
            1,
            int(max(1.0, height - self.padding * 2.0) // self.cell_size),
        )
        return columns, rows, float(visible_rows), float(self.cell_size)

    def _index_at(self, x: float, y: float) -> int | None:
        if self.tileset is None or not self.contains_point(x, y):
            return None
        center_x, center_y = self.calculate_position()
        left = center_x - self.size[0] * 0.5 + self.padding
        top = center_y - self.size[1] * 0.5 + self.padding
        local_x = float(x) - left
        local_y = float(y) - top
        if local_x < 0.0 or local_y < 0.0:
            return None
        columns, _rows, _visible_rows, cell_size = self._grid_metrics()
        column = int(local_x // cell_size)
        row = int(local_y // cell_size) + self.scroll_row
        if column < 0 or column >= columns:
            return None
        index = row * columns + column
        return index if self.tileset.contains(index) else None

    def update_input(self, ui_input) -> None:
        if not self.visible or not self.enabled:
            self.hovered_index = -1
            return

        mouse_x, mouse_y = ui_input.mouse_position
        index = self._index_at(mouse_x, mouse_y)
        self.hovered_index = -1 if index is None else index
        if self.contains_point(mouse_x, mouse_y):
            if ui_input.mouse_wheel_y:
                columns, rows, visible_rows, _cell_size = self._grid_metrics()
                del columns
                max_scroll = max(0, rows - int(visible_rows))
                self.scroll_row = max(
                    0,
                    min(
                        max_scroll,
                        self.scroll_row - int(ui_input.mouse_wheel_y),
                    ),
                )
                index = self._index_at(mouse_x, mouse_y)
                self.hovered_index = -1 if index is None else index

            if ui_input.mouse_left_pressed and self.hovered_index >= 0:
                self.set_selected_index(self.hovered_index, emit=True)

    def render(self, renderer) -> None:
        if not self.visible:
            return
        super().render(renderer)
        if self.tileset is None or self.texture is None:
            return

        center_x, center_y = self.calculate_position()
        left = center_x - self.size[0] * 0.5 + self.padding
        top = center_y - self.size[1] * 0.5 + self.padding
        columns, rows, visible_rows, cell_size = self._grid_metrics()
        first = self.scroll_row * columns
        last = min(
            self.tileset.tile_count,
            (self.scroll_row + int(visible_rows) + 1) * columns,
        )

        for index in range(first, last):
            column = index % columns
            row = index // columns - self.scroll_row
            x = left + column * cell_size + cell_size * 0.5
            y = top + row * cell_size + cell_size * 0.5
            background = (
                (52, 84, 125, 255)
                if index == self.selected_index
                else (45, 48, 53, 255)
                if index == self.hovered_index
                else (32, 34, 37, 255)
            )
            renderer.rect(
                x,
                y,
                cell_size - 4.0,
                cell_size - 4.0,
                color=tuple(channel / 255.0 for channel in background),
                radius=4.0,
            )
            renderer.sprite(
                self.texture,
                x,
                y,
                width=cell_size - 14.0,
                height=cell_size - 14.0,
                uv=self.tileset.uv(index),
            )
