from __future__ import annotations

from nexora.editor.ui import Rect, draw_outline, draw_rect, draw_text, rgba
from nexora.tilemap import TileProjection


class TileMapRenderingMixin:
    def _renderer_point(self, screen_x: float, screen_y: float) -> tuple[float, float]:
        return (screen_x - self.game.renderer.width / 2.0, screen_y - self.game.renderer.height / 2.0)

    def _visible_cell_bounds(self) -> tuple[int, int, int, int]:
        """Return the map-cell rectangle currently visible in the viewport."""
        if self.tilemap is None:
            return (0, -1, 0, -1)
        center_x = self.viewport.x + self.viewport.width / 2.0
        center_y = self.viewport.y + self.viewport.height / 2.0
        zoom = max(self.zoom, 1e-6)
        corners = (
            (self.viewport.x, self.viewport.y),
            (self.viewport.x + self.viewport.width, self.viewport.y),
            (self.viewport.x, self.viewport.y + self.viewport.height),
            (self.viewport.x + self.viewport.width, self.viewport.y + self.viewport.height),
        )
        cells = []
        for screen_x, screen_y in corners:
            local_x = self.camera_x + (screen_x - center_x) / zoom
            local_y = self.camera_y + (screen_y - center_y) / zoom
            local_x += self.tilemap.pixel_width / 2.0
            local_y += self.tilemap.pixel_height / 2.0
            cells.append(self.tilemap.world_to_tile(local_x, local_y))
        min_x = max(0, min(cell[0] for cell in cells) - 1)
        max_x = min(self.tilemap.width - 1, max(cell[0] for cell in cells) + 1)
        min_y = max(0, min(cell[1] for cell in cells) - 1)
        max_y = min(self.tilemap.height - 1, max(cell[1] for cell in cells) + 1)
        return min_x, max_x, min_y, max_y

    def _render_map(self, renderer) -> None:
        if self.tilemap is None:
            return
        center_x = self.viewport.x + self.viewport.width / 2.0
        center_y = self.viewport.y + self.viewport.height / 2.0
        min_x, max_x, min_y, max_y = self._visible_cell_bounds()
        visible_layers = sorted(enumerate(self.tilemap.layers), key=lambda item: (item[1].render_layer, item[0]))
        for _index, layer in visible_layers:
            if not layer.visible or not layer.enabled:
                continue
            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    tile_id = layer.get_tile(x, y)
                    if tile_id < 0:
                        continue
                    local_x, local_y = self.tilemap.tile_to_world(x, y)
                    local_x -= self.tilemap.pixel_width / 2.0
                    local_y -= self.tilemap.pixel_height / 2.0
                    screen_x = center_x + (local_x - self.camera_x) * self.zoom
                    screen_y = center_y + (local_y - self.camera_y) * self.zoom
                    if not self.viewport.contains(screen_x, screen_y):
                        continue
                    draw_x, draw_y = self._renderer_point(screen_x, screen_y)
                    if self.texture is not None and self.tileset is not None and self.tileset.contains(tile_id):
                        renderer.sprite(self.texture, draw_x, draw_y, width=self.tilemap.tile_width * self.zoom, height=self.tilemap.tile_height * self.zoom, uv=self.tileset.uv(tile_id), alpha=max(0.0, min(1.0, layer.opacity)))
        # A full grid is useful at editing zoom levels but becomes an
        # expensive command storm when zoomed far out.  Visible cells are
        # already clipped above, and the grid is skipped when it is too small
        # to be useful visually.
        if self.zoom < 0.35:
            return
        grid_color = rgba((52, 59, 72, 150))
        if self.tilemap.projection is not TileProjection.ISOMETRIC:
            # The orthogonal/angled editor grid is made from shared boundary
            # lines.  Drawing one rectangle plus two lines per cell scales
            # badly on large empty maps (for example 160 x 16).
            map_left = center_x + (-self.tilemap.pixel_width / 2.0 - self.camera_x) * self.zoom
            map_top = center_y + (-self.tilemap.pixel_height / 2.0 - self.camera_y) * self.zoom
            tile_width = self.tilemap.tile_width * self.zoom
            tile_height = self.tilemap.tile_height * self.zoom
            viewport_left = self.viewport.x
            viewport_right = self.viewport.x + self.viewport.width
            viewport_top = self.viewport.y
            viewport_bottom = self.viewport.y + self.viewport.height
            line_min_x = max(viewport_left, map_left + min_x * tile_width)
            line_max_x = min(viewport_right, map_left + (max_x + 1) * tile_width)
            line_min_y = max(viewport_top, map_top + min_y * tile_height)
            line_max_y = min(viewport_bottom, map_top + (max_y + 1) * tile_height)
            if line_min_x > line_max_x or line_min_y > line_max_y:
                return
            for x in range(min_x, max_x + 2):
                screen_x = map_left + x * tile_width
                if viewport_left <= screen_x <= viewport_right:
                    draw_x, draw_top = self._renderer_point(screen_x, line_min_y)
                    _unused, draw_bottom = self._renderer_point(screen_x, line_max_y)
                    renderer.line(draw_x, draw_top, draw_x, draw_bottom, width=1.0, color=grid_color)
            for y in range(min_y, max_y + 2):
                screen_y = map_top + y * tile_height
                if viewport_top <= screen_y <= viewport_bottom:
                    draw_left, draw_y = self._renderer_point(line_min_x, screen_y)
                    draw_right, _unused = self._renderer_point(line_max_x, screen_y)
                    renderer.line(draw_left, draw_y, draw_right, draw_y, width=1.0, color=grid_color)
            return
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                local_x, local_y = self.tilemap.tile_to_world(x, y)
                local_x -= self.tilemap.pixel_width / 2.0
                local_y -= self.tilemap.pixel_height / 2.0
                screen_x = center_x + (local_x - self.camera_x) * self.zoom
                screen_y = center_y + (local_y - self.camera_y) * self.zoom
                if self.viewport.contains(screen_x, screen_y):
                    draw_x, draw_y = self._renderer_point(screen_x, screen_y)
                    renderer.rect(draw_x, draw_y, self.tilemap.tile_width * self.zoom, self.tilemap.tile_height * self.zoom, color=(0.2, 0.23, 0.28, 0.16), radius=0.0)
                    renderer.line(draw_x - self.tilemap.tile_width * self.zoom / 2.0, draw_y - self.tilemap.tile_height * self.zoom / 2.0, draw_x + self.tilemap.tile_width * self.zoom / 2.0, draw_y - self.tilemap.tile_height * self.zoom / 2.0, width=1.0, color=grid_color)
                    renderer.line(draw_x - self.tilemap.tile_width * self.zoom / 2.0, draw_y - self.tilemap.tile_height * self.zoom / 2.0, draw_x - self.tilemap.tile_width * self.zoom / 2.0, draw_y + self.tilemap.tile_height * self.zoom / 2.0, width=1.0, color=grid_color)

    def _render_palette(self, renderer, viewport_size) -> None:
        if self.tileset is None or self.texture is None:
            draw_text(renderer, "Choose a tileset image to begin.", self.bottom_panel.x + 16.0, self.bottom_panel.y + 48.0, viewport_size, scale=0.62, color=self.theme.muted)
            return
        cell_size = 62.0
        columns = max(1, int((self.bottom_panel.width - 24.0) // cell_size))
        for index in range(self.tileset.tile_count):
            column = index % columns
            row = index // columns
            x = self.bottom_panel.x + 12.0 + column * cell_size
            y = self.bottom_panel.y + 38.0 + row * cell_size
            if y + cell_size > self.bottom_panel.y + self.bottom_panel.height:
                break
            cell = Rect(x, y, cell_size - 4.0, cell_size - 4.0)
            draw_rect(renderer, cell, self.theme.selected if index == self.selected_tile else self.theme.panel_dark, viewport_size, radius=3.0)
            draw_outline(renderer, cell, self.theme.accent if index == self.selected_tile else self.theme.border, viewport_size)
            sx, sy = self._renderer_point(x + cell.width / 2.0, y + cell.height / 2.0)
            renderer.sprite(self.texture, sx, sy, width=cell.width - 12.0, height=cell.height - 12.0, uv=self.tileset.uv(index))
