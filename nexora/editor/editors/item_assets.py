from __future__ import annotations

from nexora.gameplay.items import ITEM_ASSET_SUFFIX, ItemAsset

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")


class ItemAssetsMixin:

    def _open_browser(self, mode: str) -> None:
        start = self._item_start_path() if mode in {"open", "save"} else self.assets_root
        extensions = (
            (ITEM_ASSET_SUFFIX,)
            if mode in {"open", "save"}
            else IMAGE_EXTENSIONS
        )
        self._open_file_browser(
            mode,
            root=self.project_path,
            start=start,
            extensions=extensions,
            filename=f"{self.item.item_id}{ITEM_ASSET_SUFFIX}" if mode == "save" else "",
        )

    def _browser_selected(self, index: int) -> None:
        path = self._select_browser_entry(index)
        if path is None:
            return
        if self.browser_mode == "icon":
            self.fields["icon"].set_text(self._asset_relative(path))
            self._load_icon_texture()
            self.dirty = True
            self.status = f"Icon selected: {path.name}"
            self._close_modal()
        elif self.browser_mode == "open":
            self._load_item_path(path)
            self._close_modal()
        else:
            self.browser_name.set_text(path.name)
            self.status = f"Save as {path.name}"


    def _browser_action(self) -> None:
        if self.browser_mode == "save":
            self._save_from_browser()

    def _save_from_browser(self) -> None:
        name = self.browser_name.text.strip() or f"{self.item.item_id}{ITEM_ASSET_SUFFIX}"
        if not name.lower().endswith(ITEM_ASSET_SUFFIX):
            name += ITEM_ASSET_SUFFIX
        self.item = self._collect_item()
        path = self.browser_path / name
        try:
            self.document_path = ItemAsset(self.item).save(path)
            self.dirty = False
            self.refresh_item_list()
            self.status = f"Saved {self._project_relative(self.document_path)}"
            self._close_modal()
        except Exception as exc:
            self.status = f"Could not save item: {exc}"

    def _load_icon_texture(self) -> None:
        self.icon_texture = None
        icon = self.fields["icon"].text.strip()
        if not icon or self.game.engine is None:
            return
        path = self._asset_path(icon)
        if path.is_file():
            try:
                self.icon_texture = self.game.engine.assets.texture(path)
            except Exception:
                self.icon_texture = None
