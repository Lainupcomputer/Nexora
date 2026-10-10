from __future__ import annotations

from pathlib import Path

from nexora.tilemap import TILEMAP_ASSET_SUFFIX, TileMap, TileMapAsset, TileProjection, TileSet


class TileMapDocumentMixin:
    def new_map(self) -> None:
        self.tilemap = TileMap(
            name="Untitled",
            width=16,
            height=16,
            tile_width=32,
            tile_height=32,
            projection=TileProjection.ANGLED_2D,
        )
        self.tilemap.create_layer("ground", role="ground")
        self.tileset = None
        self.texture = None
        self.document_path = None
        self.document_name = "Untitled"
        self.pending_tileset_path = None
        self.active_layer_name = "ground"
        self.selected_tile = 0
        self.commands.clear()
        self.dirty = False
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.status = "New TileMap"
        self._refresh_layer_controls()
        self._refresh_map_controls()

    def open_map(self) -> None:
        self._open_browser("map_open")

    def save_map(self) -> None:
        if self.document_path is None:
            self.save_map_as()
            return
        self._save_asset(self.document_path)

    def save_map_as(self) -> None:
        self._open_browser("map_save")
        self.browser_name.set_text(f"{self.document_name}{TILEMAP_ASSET_SUFFIX}")

    def _save_asset(self, path: Path) -> None:
        if self.tilemap is None or self.tileset is None or not self.tileset.texture_asset:
            self.status = "Choose and configure a tileset before saving."
            return
        saved = TileMapAsset.from_components(self.tilemap, self.tileset, name=self.document_name).save(path)
        self.document_path = saved
        self.tilemap.name = self.document_name
        self.dirty = False
        self.status = f"Saved {saved.name}"

    def _load_asset(self, path: Path) -> None:
        try:
            asset = TileMapAsset.load(path)
            self.tilemap, self.tileset = asset.build()
            if not self.tileset.texture_asset:
                raise ValueError("TileMap asset has no tileset texture.")
            texture_path = self._asset_path(self.tileset.texture_asset)
            self.texture = self.game.engine.assets.texture(texture_path)
            self.document_path = path.resolve()
            self.document_name = asset.name
            self.active_layer_name = self.tilemap.layer_names[0] if self.tilemap.layer_names else None
            self.commands.clear()
            self.dirty = False
            self.status = f"Opened {path.name}"
            self._refresh_layer_controls()
            self._refresh_map_controls()
        except Exception as exc:
            self.status = f"Could not open TileMap: {exc}"

    def open_tileset_browser(self) -> None:
        self._open_browser("tileset")

    def _open_browser(self, mode: str) -> None:
        extensions = (
            (".png", ".jpg", ".jpeg", ".bmp", ".webp")
            if mode == "tileset"
            else (TILEMAP_ASSET_SUFFIX,)
        )
        self._open_file_browser(
            mode,
            root=self.project_path,
            start=self._asset_root(),
            extensions=extensions,
            filename="",
        )

    def _browser_selected(self, index: int) -> None:
        path = self._select_browser_entry(index)
        if path is None:
            return
        if self.browser_mode == "tileset":
            self._begin_tileset_setup(path)
        elif self.browser_mode == "map_save":
            # Save As must never open an existing asset.  Selecting one in
            # the browser only chooses its filename; the Save button then
            # performs the actual overwrite.
            self.browser_name.set_text(path.name)
            self.status = f"Save as {path.name}"
        else:
            self._load_asset(path)
            self._close_modal()

    def _save_from_browser(self) -> None:
        name = self.browser_name.text.strip() or f"{self.document_name}{TILEMAP_ASSET_SUFFIX}"
        if not name.lower().endswith(TILEMAP_ASSET_SUFFIX):
            name += TILEMAP_ASSET_SUFFIX
        self._save_asset(self.browser_path / name)
        self._close_modal()

    def _begin_tileset_setup(self, path: Path) -> None:
        try:
            image = self.game.engine.assets.image(path)
        except Exception as exc:
            self.status = f"Could not read image: {exc}"
            return
        self.pending_tileset_path = path.resolve()
        self.tileset_image_size = (int(image.width), int(image.height))
        self.modal = "setup"
        self.setup_error = ""
        for name, value in (
            ("tile_width", self.tilemap.tile_width if self.tilemap else 32),
            ("tile_height", self.tilemap.tile_height if self.tilemap else 32),
            ("gap_x", 0),
            ("gap_y", 0),
            ("margin_x", 0),
            ("margin_y", 0),
        ):
            self.setup_fields[name].set_text(str(value))
        self._update_setup_summary()

    def _setup_int(self, name: str, default: int = 0) -> int:
        try:
            return int(self.setup_fields[name].text.strip())
        except (TypeError, ValueError):
            return default

    def _update_setup_summary(self) -> None:
        if self.tileset_image_size is None:
            self.setup_summary = ""
            return
        image_width, image_height = self.tileset_image_size
        tile_width = self._setup_int("tile_width", 32)
        tile_height = self._setup_int("tile_height", 32)
        gap_x = self._setup_int("gap_x", 0)
        gap_y = self._setup_int("gap_y", 0)
        margin_x = self._setup_int("margin_x", 0)
        margin_y = self._setup_int("margin_y", 0)
        usable_width = image_width - margin_x * 2
        usable_height = image_height - margin_y * 2
        if tile_width <= 0 or tile_height <= 0 or gap_x < 0 or gap_y < 0 or usable_width <= 0 or usable_height <= 0:
            self.setup_summary = "Invalid values."
            return
        columns = (usable_width + gap_x) // (tile_width + gap_x)
        rows = (usable_height + gap_y) // (tile_height + gap_y)
        exact = (
            columns > 0
            and rows > 0
            and columns * tile_width + max(0, columns - 1) * gap_x == usable_width
            and rows * tile_height + max(0, rows - 1) * gap_y == usable_height
        )
        self.setup_summary = f"Image: {image_width} x {image_height} px   |   Grid: {columns} x {rows} tiles" if exact else "Grid does not fit the image exactly."

    def _apply_setup(self) -> None:
        if self.pending_tileset_path is None or self.tilemap is None or self.tileset_image_size is None:
            return
        image_width, image_height = self.tileset_image_size
        tile_width = self._setup_int("tile_width", 32)
        tile_height = self._setup_int("tile_height", 32)
        gap_x = self._setup_int("gap_x", 0)
        gap_y = self._setup_int("gap_y", 0)
        margin_x = self._setup_int("margin_x", 0)
        margin_y = self._setup_int("margin_y", 0)
        usable_width = image_width - margin_x * 2
        usable_height = image_height - margin_y * 2
        if tile_width <= 0 or tile_height <= 0 or gap_x < 0 or gap_y < 0 or usable_width <= 0 or usable_height <= 0:
            self.setup_error = "Tile size, gap and margin values are invalid."
            return
        columns = (usable_width + gap_x) // (tile_width + gap_x)
        rows = (usable_height + gap_y) // (tile_height + gap_y)
        expected_width = columns * tile_width + max(0, columns - 1) * gap_x
        expected_height = rows * tile_height + max(0, rows - 1) * gap_y
        if columns <= 0 or rows <= 0 or expected_width != usable_width or expected_height != usable_height:
            self.setup_error = "Grid does not fit. Adjust Tile Size, Gap or Margin."
            return
        try:
            asset_path = self._asset_relative(self.pending_tileset_path)
            self.tileset = TileSet(
                name=self.pending_tileset_path.stem,
                columns=columns,
                rows=rows,
                tile_width=tile_width,
                tile_height=tile_height,
                texture_asset=asset_path,
                spacing_x=gap_x,
                spacing_y=gap_y,
                margin_x=margin_x,
                margin_y=margin_y,
            )
            self.tilemap.tile_width = tile_width
            self.tilemap.tile_height = tile_height
            self.texture = self.game.engine.assets.texture(self.pending_tileset_path)
            self.dirty = True
            self.modal = None
            self.status = f"Tileset loaded: {columns} x {rows} tiles"
        except Exception as exc:
            self.setup_error = str(exc)
