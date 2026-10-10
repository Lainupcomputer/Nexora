from __future__ import annotations

from nexora.gameplay.items import ITEM_ASSET_SUFFIX, ItemAsset


class ItemCatalogMixin:

    def refresh_item_list(self, *, rebuild_catalog: bool = True) -> None:
        entries = sorted(self.items_root.rglob(f"*{ITEM_ASSET_SUFFIX}"), key=lambda path: str(path).lower()) if self.items_root.is_dir() else []
        self._item_entries = entries
        if rebuild_catalog or not hasattr(self, "_item_catalog"):
            self._item_catalog = {}
            for path in entries:
                try:
                    item = ItemAsset.load(path).item
                    category = item.category.replace("_", " ").title() or "Misc"
                    label = f"{item.name}  [{item.item_id}]"
                except Exception:
                    category = "Invalid"
                    label = path.name
                self._item_catalog[path] = (category, label)
        query = self.item_search.text.strip().lower()
        groups: dict[str, list[tuple[str, int]]] = {}
        for index, path in enumerate(entries):
            category, label = self._item_catalog[path]
            relative = self._asset_relative(path)
            search_text = f"{label} {relative}".lower()
            if query and query not in search_text:
                continue
            groups.setdefault(category, []).append((label, index))
        self.item_list.set_groups(dict(sorted(groups.items(), key=lambda pair: pair[0].lower())))

    def _item_search_changed(self, _value: str) -> None:
        if not self._loading:
            self.refresh_item_list(rebuild_catalog=False)

    def _item_selected(self, index: int) -> None:
        entries = getattr(self, "_item_entries", [])
        if 0 <= index < len(entries):
            self._load_item_path(entries[index])
