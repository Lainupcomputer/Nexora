from __future__ import annotations

from nexora.tilemap import TileMap
from nexora.tilemap.tile_layer import LAYER_ROLES, normalize_layer_role


class TileMapLayerMixin:
    def _active_layer(self):
        if self.tilemap is None or self.active_layer_name is None:
            return None
        try:
            return self.tilemap.require_layer(self.active_layer_name)
        except KeyError:
            return None

    def _refresh_layer_controls(self) -> None:
        if self.tilemap is None:
            self.layer_list.set_items([])
            return
        self.layer_list.set_items([
            f"{layer.name} [{normalize_layer_role(layer.role, name=layer.name).title()}]"
            for layer in self.tilemap.layers
        ])
        if self.active_layer_name in self.tilemap.layer_names:
            self.layer_list.selected = self.tilemap.layer_names.index(self.active_layer_name)
        layer = self._active_layer()
        if layer is None:
            return
        self.layer_name.set_text(layer.name)
        self.layer_role.selected = LAYER_ROLES.index(normalize_layer_role(layer.role, name=layer.name))
        self.layer_visible.checked = layer.visible
        self.layer_enabled.checked = layer.enabled
        self.layer_render.set_text(str(layer.render_layer))
        self.layer_opacity.set_text(f"{layer.opacity:.2f}")
        self.layer_y_sort.checked = layer.y_sort

    def _layer_selected(self, index: int) -> None:
        if self.tilemap is None or not (0 <= index < len(self.tilemap.layers)):
            return
        self.active_layer_name = self.tilemap.layers[index].name
        self._refresh_layer_controls()

    def _add_layer(self) -> None:
        if self.tilemap is None:
            return
        base = "Layer"
        index = 1
        while f"{base} {index}" in self.tilemap:
            index += 1
        self.tilemap.create_layer(f"{base} {index}", role="custom")
        self.active_layer_name = f"{base} {index}"
        self.dirty = True
        self._refresh_layer_controls()

    def _remove_layer(self) -> None:
        if self.tilemap is None or self.active_layer_name is None or self.tilemap.layer_count <= 1:
            return
        index = self.tilemap.layer_index(self.active_layer_name)
        self.tilemap.remove_layer(self.active_layer_name)
        self.active_layer_name = self.tilemap.layers[max(0, index - 1)].name
        self.dirty = True
        self._refresh_layer_controls()

    def _layer_is_visible(self, index: int) -> bool:
        return bool(self.tilemap is not None and 0 <= index < self.tilemap.layer_count and self.tilemap.layers[index].visible)

    def _toggle_layer_visibility(self, index: int) -> None:
        if self.tilemap is None or not (0 <= index < self.tilemap.layer_count):
            return
        layer = self.tilemap.layers[index]
        layer.visible = not layer.visible
        self.dirty = True
        self.status = f"Layer {layer.name}: {'visible' if layer.visible else 'hidden'}"
        self._refresh_layer_controls()

    def _move_layer_up(self) -> None:
        if self.tilemap is None or self.active_layer_name is None:
            return
        self.tilemap.move_layer_down(self.active_layer_name)
        self.dirty = True
        self._refresh_layer_controls()
        self.status = f"Layer moved up: {self.active_layer_name}"

    def _move_layer_down(self) -> None:
        if self.tilemap is None or self.active_layer_name is None:
            return
        self.tilemap.move_layer_up(self.active_layer_name)
        self.dirty = True
        self._refresh_layer_controls()
        self.status = f"Layer moved down: {self.active_layer_name}"

    def _refresh_map_controls(self) -> None:
        if self.tilemap is None:
            return
        self.map_width.set_text(str(self.tilemap.width))
        self.map_height.set_text(str(self.tilemap.height))

    def _apply_map_size(self) -> None:
        if self.tilemap is None:
            return
        try:
            width = max(1, min(4096, int(self.map_width.text.strip())))
            height = max(1, min(4096, int(self.map_height.text.strip())))
        except ValueError:
            self.status = "Invalid map size."
            self._refresh_map_controls()
            return
        if (width, height) == (self.tilemap.width, self.tilemap.height):
            self.status = "Map size unchanged."
            return

        old_map = self.tilemap
        resized = TileMap(
            name=old_map.name,
            width=width,
            height=height,
            tile_width=old_map.tile_width,
            tile_height=old_map.tile_height,
            projection=old_map.projection,
        )
        for old_layer in old_map.layers:
            new_layer = resized.create_layer(
                old_layer.name,
                visible=old_layer.visible,
                enabled=old_layer.enabled,
                opacity=old_layer.opacity,
                render_layer=old_layer.render_layer,
                y_sort=old_layer.y_sort,
                role=old_layer.role,
            )
            copy_width = min(old_map.width, width)
            copy_height = min(old_map.height, height)
            for y in range(copy_height):
                for x in range(copy_width):
                    tile_id = old_layer.get_tile(x, y)
                    if tile_id >= 0:
                        new_layer.set_tile(x, y, tile_id)
        self.tilemap = resized
        self.commands.clear()
        self.dirty = True
        self._refresh_layer_controls()
        self._refresh_map_controls()
        self.status = f"Map resized to {width} x {height}"

    def _rename_active_layer(self) -> None:
        layer = self._active_layer()
        name = self.layer_name.text.strip()
        if layer is None or not name or name == layer.name:
            return
        try:
            self.tilemap.rename_layer(layer, name)
            self.active_layer_name = name
            self.dirty = True
            self._refresh_layer_controls()
        except Exception as exc:
            self.status = str(exc)

    def _role_changed(self, index: int, _value: str) -> None:
        if not (0 <= index < len(LAYER_ROLES)):
            return
        self._set_layer_property("role", LAYER_ROLES[index])

    def _set_layer_property(self, name: str, value) -> None:
        layer = self._active_layer()
        if layer is None:
            return
        if name == "role":
            value = normalize_layer_role(value, name=layer.name)
        setattr(layer, name, value)
        self.dirty = True
        self._refresh_layer_controls()

    def _submit_layer_number(self, name: str) -> None:
        layer = self._active_layer()
        if layer is None:
            return
        try:
            value = int(self.layer_render.text) if name == "render_layer" else max(0.0, min(1.0, float(self.layer_opacity.text)))
            setattr(layer, name, value)
            self.dirty = True
            self._refresh_layer_controls()
        except ValueError:
            self.status = f"Invalid {name}."
