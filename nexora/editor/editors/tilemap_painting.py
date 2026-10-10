from __future__ import annotations

from nexora.editor.commands import TileMapCellEdit, TileMapPaintCommand


class TileMapPaintingMixin:
    def _set_tool(self, tool: str) -> None:
        self.tool = str(tool)
        self.status = f"Tool: {self.tool.title()}"

    def _paint_cell(self, cell: tuple[int, int], tile_id: int) -> None:
        layer = self._active_layer()
        if layer is None or self.tilemap is None or not self.tilemap.contains(*cell):
            return
        if cell not in self.stroke_edits:
            self.stroke_edits[cell] = layer.get_tile(*cell)
        if tile_id < 0:
            layer.clear_tile(*cell)
        else:
            layer.set_tile(*cell, tile_id)

    def _finish_stroke(self) -> None:
        layer = self.stroke_layer
        if layer is None:
            return
        edits = [TileMapCellEdit(x, y, before, layer.get_tile(x, y)) for (x, y), before in self.stroke_edits.items()]
        command = TileMapPaintCommand(layer, edits, label="Paint Tiles" if self.stroke_tile >= 0 else "Erase Tiles")
        if command.edits:
            self.commands.execute(command)
            self.dirty = True
        self.stroke_layer = None
        self.stroke_tile = None
        self.stroke_edits.clear()

    def _fill_layer(self) -> None:
        layer = self._active_layer()
        if layer is None or self.tileset is None:
            return
        edits = [TileMapCellEdit(x, y, layer.get_tile(x, y), self.selected_tile) for y in range(layer.height) for x in range(layer.width)]
        command = TileMapPaintCommand(layer, edits, label="Fill Layer")
        if command.edits:
            self.commands.execute(command)
            self.dirty = True

    def undo(self) -> None:
        if self.commands.undo() is not None:
            self.dirty = True
            self.status = "Undo"

    def redo(self) -> None:
        if self.commands.redo() is not None:
            self.dirty = True
            self.status = "Redo"

    def _viewport_cell(self, mouse_x: float, mouse_y: float) -> tuple[int, int] | None:
        if self.tilemap is None or not self.viewport.contains(mouse_x, mouse_y):
            return None
        center_x = self.viewport.x + self.viewport.width / 2.0
        center_y = self.viewport.y + self.viewport.height / 2.0
        local_x = self.camera_x + (mouse_x - center_x) / max(self.zoom, 1e-6)
        local_y = self.camera_y + (mouse_y - center_y) / max(self.zoom, 1e-6)
        local_x += self.tilemap.pixel_width / 2.0
        local_y += self.tilemap.pixel_height / 2.0
        cell = self.tilemap.world_to_tile(local_x, local_y)
        return cell if self.tilemap.contains(*cell) else None

    def _update_viewport(self, input_manager, mouse_x: float, mouse_y: float) -> None:
        if self.modal is not None:
            return
        if input_manager.key_pressed("home"):
            self.camera_x = self.camera_y = 0.0
            self.zoom = 1.0
        if self.viewport.contains(mouse_x, mouse_y):
            _wheel_x, wheel_y = input_manager.wheel
            if wheel_y:
                self.zoom = max(0.15, min(6.0, self.zoom * (1.15 ** float(wheel_y))))
            if input_manager.mouse_down("middle"):
                dx, dy = input_manager.mouse_delta
                self.camera_x -= dx / max(self.zoom, 1e-6)
                self.camera_y -= dy / max(self.zoom, 1e-6)
            cell = self._viewport_cell(mouse_x, mouse_y)
            if self.tool == "fill" and input_manager.mouse_pressed("left") and cell is not None:
                self._fill_layer()
                return
            if self.tool in {"paint", "erase"}:
                left_held = input_manager.mouse_pressed("left") or input_manager.mouse_down("left")
                if left_held and cell is not None:
                    if self.stroke_layer is None:
                        self.stroke_layer = self._active_layer()
                        self.stroke_tile = self.selected_tile if self.tool == "paint" else -1
                    # Tile ID 0 is a valid tile and must not be treated as
                    # EMPTY_TILE while a drag is continued.
                    tile_id = self.stroke_tile if self.stroke_tile is not None else -1
                    self._paint_cell(cell, tile_id)
                if self.stroke_layer is not None and input_manager.mouse_released("left"):
                    self._finish_stroke()
            if self.tool == "select" and input_manager.mouse_pressed("left") and cell is not None:
                layer = self._active_layer()
                if layer is not None and layer.get_tile(*cell) >= 0:
                    self.selected_tile = layer.get_tile(*cell)

    def _palette_tile_at(self, mouse_x: float, mouse_y: float) -> int | None:
        if self.tileset is None or self.texture is None or not self.bottom_panel.contains(mouse_x, mouse_y):
            return None
        cell_size = 62.0
        columns = max(1, int((self.bottom_panel.width - 24.0) // cell_size))
        local_x = mouse_x - (self.bottom_panel.x + 12.0)
        local_y = mouse_y - (self.bottom_panel.y + 38.0)
        if local_x < 0.0 or local_y < 0.0:
            return None
        column = int(local_x // cell_size)
        row = int(local_y // cell_size)
        within_x = local_x - column * cell_size
        within_y = local_y - row * cell_size
        if within_x > cell_size - 4.0 or within_y > cell_size - 4.0:
            return None
        index = row * columns + column
        return index if 0 <= index < self.tileset.tile_count else None

    def _update_palette(self, input_manager, mouse_x: float, mouse_y: float) -> None:
        if input_manager.mouse_pressed("left"):
            tile_id = self._palette_tile_at(mouse_x, mouse_y)
            if tile_id is not None:
                self.selected_tile = tile_id
                self.tool = "paint"
                self.status = f"Selected tile {tile_id}"
