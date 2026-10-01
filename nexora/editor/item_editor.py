from __future__ import annotations

"""Standalone editor for Nexora ``.nitem`` resources."""

from pathlib import Path

from nexora import Game
from nexora.editor.app import resolve_project_path
from nexora.editor.model import EditorProjectContext
from nexora.editor.ui import (
    Button,
    CategorizedListBox,
    CheckBox,
    Dropdown,
    ListBox,
    Menu,
    Rect,
    TextField,
    UITheme,
    FileBrowserModel,
    centered_rect,
    close_other_menus,
    draw_outline,
    draw_rect,
    draw_text,
    sync_browser_list,
)
from nexora.items import ITEM_ASSET_SUFFIX, ItemAsset, ItemDefinition
from nexora.scene import Scene


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
def _number(value: str, default: float = 0.0) -> float:
    try:
        return float(value.strip())
    except (TypeError, ValueError):
        return float(default)


def _integer(value: str, default: int = 0) -> int:
    try:
        return int(float(value.strip()))
    except (TypeError, ValueError):
        return int(default)


class ItemEditorScene(Scene):
    """Renderer-backed item authoring scene with a custom standalone UI."""

    TOOLBAR_HEIGHT = 58.0
    STATUS_HEIGHT = 30.0
    LEFT_WIDTH = 300.0
    PREVIEW_WIDTH = 320.0

    def __init__(
        self,
        game,
        project_path: Path,
        item_path: str | Path | None = None,
        project_context: EditorProjectContext | None = None,
    ) -> None:
        super().__init__("StandaloneItemEditor")
        self.game = game
        self.project_context = project_context or EditorProjectContext.from_path(project_path)
        self.project_path = self.project_context.root
        self.assets_root = self.project_context.assets_root
        self.items_root = self.project_context.items_root
        self.theme = UITheme()
        self.item = ItemDefinition()
        self.document_path: Path | None = None
        self.dirty = False
        self.status = "Ready"
        self.modal: str | None = None
        self.browser_mode = "open"
        self.browser_root = self.project_path
        self.browser_path = self._item_start_path()
        self.browser_entries: list[Path] = []
        self.file_browser = FileBrowserModel()
        self.icon_texture = None
        self._layout_size = (-1.0, -1.0)
        self._loading = False
        self.active_tab = "General"
        self.tab_names = ("General", "Gameplay", "Use", "Effects", "Crafting", "Loot", "Shop")
        self.effect_capacity = 4
        self.ingredient_capacity = 6
        self._tab_layouts: dict[str, list[tuple[str, str, float, float, float]]] = {}

        self.fields = {
            "id": TextField(Rect(0, 0, 1, 1), "new_item"),
            "name": TextField(Rect(0, 0, 1, 1), "New Item"),
            "description": TextField(Rect(0, 0, 1, 1), ""),
            "max_stack": TextField(Rect(0, 0, 1, 1), "1"),
            "value": TextField(Rect(0, 0, 1, 1), "0"),
            "weight": TextField(Rect(0, 0, 1, 1), "0.0"),
            "equip_slot": TextField(Rect(0, 0, 1, 1), "none"),
            "tags": TextField(Rect(0, 0, 1, 1), ""),
            "icon": TextField(Rect(0, 0, 1, 1), ""),
            "weapon_damage": TextField(Rect(0, 0, 1, 1), "0"),
            "weapon_speed": TextField(Rect(0, 0, 1, 1), "1.0"),
            "weapon_range": TextField(Rect(0, 0, 1, 1), "1.0"),
            "tool_type": TextField(Rect(0, 0, 1, 1), ""),
            "tool_power": TextField(Rect(0, 0, 1, 1), "0"),
            "durability": TextField(Rect(0, 0, 1, 1), "0"),
            "armor_defense": TextField(Rect(0, 0, 1, 1), "0"),
            "armor_resistance": TextField(Rect(0, 0, 1, 1), "0"),
            "consumable_health": TextField(Rect(0, 0, 1, 1), "0"),
            "consumable_stamina": TextField(Rect(0, 0, 1, 1), "0"),
            "consumable_mana": TextField(Rect(0, 0, 1, 1), "0"),
            "effect_type": TextField(Rect(0, 0, 1, 1), ""),
            "effect_value": TextField(Rect(0, 0, 1, 1), "0"),
            "effect_duration": TextField(Rect(0, 0, 1, 1), "0"),
            "effect_status": TextField(Rect(0, 0, 1, 1), ""),
            "crafting_station": TextField(Rect(0, 0, 1, 1), ""),
            "crafting_time": TextField(Rect(0, 0, 1, 1), "0"),
            "crafting_output": TextField(Rect(0, 0, 1, 1), "1"),
            "ingredient_1": TextField(Rect(0, 0, 1, 1), ""),
            "ingredient_1_count": TextField(Rect(0, 0, 1, 1), "1"),
            "ingredient_2": TextField(Rect(0, 0, 1, 1), ""),
            "ingredient_2_count": TextField(Rect(0, 0, 1, 1), "1"),
            "loot_min": TextField(Rect(0, 0, 1, 1), "1"),
            "loot_max": TextField(Rect(0, 0, 1, 1), "1"),
            "loot_chance": TextField(Rect(0, 0, 1, 1), "1.0"),
            "loot_weight": TextField(Rect(0, 0, 1, 1), "1.0"),
            "loot_source": TextField(Rect(0, 0, 1, 1), ""),
            "loot_table": TextField(Rect(0, 0, 1, 1), ""),
            "loot_conditions": TextField(Rect(0, 0, 1, 1), ""),
            "req_level": TextField(Rect(0, 0, 1, 1), "0"),
            "req_skill": TextField(Rect(0, 0, 1, 1), ""),
            "req_skill_level": TextField(Rect(0, 0, 1, 1), "0"),
            "world_sprite": TextField(Rect(0, 0, 1, 1), ""),
            "drop_sprite": TextField(Rect(0, 0, 1, 1), ""),
            "author": TextField(Rect(0, 0, 1, 1), ""),
            "guid": TextField(Rect(0, 0, 1, 1), ""),
            "notes": TextField(Rect(0, 0, 1, 1), ""),
            "use_cooldown": TextField(Rect(0, 0, 1, 1), "0"),
            "use_animation": TextField(Rect(0, 0, 1, 1), ""),
            "use_callback": TextField(Rect(0, 0, 1, 1), ""),
            "equip_callback": TextField(Rect(0, 0, 1, 1), ""),
            "drop_callback": TextField(Rect(0, 0, 1, 1), ""),
            "pickup_sound": TextField(Rect(0, 0, 1, 1), ""),
            "use_sound": TextField(Rect(0, 0, 1, 1), ""),
            "equip_sound": TextField(Rect(0, 0, 1, 1), ""),
            "drop_sound": TextField(Rect(0, 0, 1, 1), ""),
            "bonus_health": TextField(Rect(0, 0, 1, 1), "0"),
            "bonus_stamina": TextField(Rect(0, 0, 1, 1), "0"),
            "bonus_mana": TextField(Rect(0, 0, 1, 1), "0"),
            "bonus_move_speed": TextField(Rect(0, 0, 1, 1), "0"),
            "bonus_sprint": TextField(Rect(0, 0, 1, 1), "0"),
            "bonus_sneak": TextField(Rect(0, 0, 1, 1), "0"),
            "shop_buy": TextField(Rect(0, 0, 1, 1), "0"),
            "shop_sell": TextField(Rect(0, 0, 1, 1), "0"),
            "shop_stock": TextField(Rect(0, 0, 1, 1), "-1"),
            "shop_vendor": TextField(Rect(0, 0, 1, 1), ""),
            "shop_unlock_level": TextField(Rect(0, 0, 1, 1), "0"),
            "shop_currency": TextField(Rect(0, 0, 1, 1), "gold"),
        }
        for index in range(1, self.effect_capacity + 1):
            self.fields.update({
                f"effect_{index}_type": TextField(Rect(0, 0, 1, 1), ""),
                f"effect_{index}_value": TextField(Rect(0, 0, 1, 1), "0"),
                f"effect_{index}_duration": TextField(Rect(0, 0, 1, 1), "0"),
                f"effect_{index}_status": TextField(Rect(0, 0, 1, 1), ""),
            })
        for index in range(3, self.ingredient_capacity + 1):
            self.fields.update({
                f"ingredient_{index}": TextField(Rect(0, 0, 1, 1), ""),
                f"ingredient_{index}_count": TextField(Rect(0, 0, 1, 1), "1"),
            })
        for field in self.fields.values():
            field.on_change = self._field_changed

        self.category = Dropdown(Rect(0, 0, 1, 1), ("Misc", "Weapon", "Tool", "Armor", "Consumable", "Material", "Quest"), on_change=self._dropdown_changed)
        self.rarity = Dropdown(Rect(0, 0, 1, 1), ("Common", "Uncommon", "Rare", "Epic", "Legendary"), on_change=self._dropdown_changed)
        self.usable = CheckBox(Rect(0, 0, 1, 1), "Usable", False, self._check_changed)
        self.equippable = CheckBox(Rect(0, 0, 1, 1), "Equippable", False, self._check_changed)
        self.can_buy = CheckBox(Rect(0, 0, 1, 1), "Can Buy", True, self._check_changed)
        self.can_sell = CheckBox(Rect(0, 0, 1, 1), "Can Sell", True, self._check_changed)
        self.use_action = Dropdown(Rect(0, 0, 1, 1), ("None", "Consume", "Equip", "Throw", "Place", "Open", "Interact"), on_change=self._dropdown_changed)
        self.use_target = Dropdown(Rect(0, 0, 1, 1), ("Self", "Target", "Area", "Inventory"), on_change=self._dropdown_changed)

        self.tab_buttons = []
        for tab_name in self.tab_names:
            button = Button(Rect(0, 0, 1, 1), tab_name, lambda tab=tab_name: self._set_tab(tab))
            button.text_scale = 0.54
            self.tab_buttons.append(button)

        self.item_search = TextField(Rect(0, 0, 1, 1), "", "Search items...")
        self.item_search.on_change = self._item_search_changed
        self.item_list = CategorizedListBox(Rect(0, 0, 1, 1), self._item_selected)
        self.new_button = Button(Rect(0, 0, 1, 1), "New", self.new_item)
        self.open_button = Button(Rect(0, 0, 1, 1), "Open", lambda: self._open_browser("open"))
        self.save_button = Button(Rect(0, 0, 1, 1), "Save", self.save_item)
        self.icon_button = Button(Rect(0, 0, 1, 1), "Choose Icon", lambda: self._open_browser("icon"))
        self.browser_list = ListBox(Rect(0, 0, 1, 1), self._browser_selected)
        self.browser_cancel_button = Button(Rect(0, 0, 1, 1), "Cancel", self._close_modal)
        self.browser_save_button = Button(Rect(0, 0, 1, 1), "Save", self._save_from_browser)
        self.browser_name = TextField(Rect(0, 0, 1, 1), "", "File name")
        self.info_close_button = Button(Rect(0, 0, 1, 1), "Close", self._close_modal)

        self.file_menu = Menu(Rect(0, 0, 1, 1), "File", [
            ("New", self.new_item),
            ("Open", lambda: self._open_browser("open")),
            ("Save", self.save_item),
            ("Save As", lambda: self._open_browser("save")),
            ("Exit", self.game.stop),
        ])
        self.item_menu = Menu(Rect(0, 0, 1, 1), "Item", [
            ("Choose Icon", lambda: self._open_browser("icon")),
            ("Refresh Items", self.refresh_item_list),
            ("Validate Item", self.validate_item),
        ])
        self.help_menu = Menu(Rect(0, 0, 1, 1), "Help", [("About Item Assets", self._show_about)])
        self.menus = [self.file_menu, self.item_menu, self.help_menu]
        for menu in self.menus:
            menu.on_open = self._menu_opened

        self.info_title = ""
        self.info_lines: tuple[str, ...] = ()
        self.new_item()
        self.refresh_item_list()
        if item_path is not None:
            self._load_item_path(self._resolve_requested_path(item_path))

    # ------------------------------------------------------------------
    # Project and item paths
    # ------------------------------------------------------------------

    def _asset_root(self) -> Path:
        return self.project_context.assets_root

    def _item_start_path(self) -> Path:
        return self.project_context.items_root if self.items_root.is_dir() else self.project_path

    def _asset_relative(self, path: Path) -> str:
        return self.project_context.relative_asset(path, root=self.assets_root)

    def _asset_path(self, value: str | Path) -> Path:
        return self.project_context.resolve_asset(value)

    def _resolve_requested_path(self, value: str | Path) -> Path:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
        return self.project_context.resolve_project_file(
            path,
            roots=(self.items_root, self.assets_root),
        )

    # ------------------------------------------------------------------
    # Item state
    # ------------------------------------------------------------------

    def _set_tab(self, tab_name: str) -> None:
        if tab_name in self.tab_names:
            self.active_tab = tab_name
            for button in self.tab_buttons:
                button.selected = button.text == tab_name
            self.status = f"{tab_name} tab"

    def new_item(self) -> None:
        self.item = ItemDefinition()
        self.document_path = None
        self.dirty = False
        self._load_controls()
        self._load_icon_texture()
        self.status = "New item"

    def _load_item_path(self, path: Path) -> None:
        try:
            asset = ItemAsset.load(path)
            self.item = asset.item
            self.document_path = path.resolve()
            self.dirty = False
            self._load_controls()
            self._load_icon_texture()
            self.status = f"Opened {path.name}"
        except Exception as exc:
            self.status = f"Could not open item: {exc}"

    def _collect_item(self) -> ItemDefinition:
        effects = []
        for index in range(1, self.effect_capacity + 1):
            effect_type = self.fields[f"effect_{index}_type"].text.strip()
            if effect_type:
                effects.append({
                    "type": effect_type,
                    "value": _number(self.fields[f"effect_{index}_value"].text),
                    "duration": max(0.0, _number(self.fields[f"effect_{index}_duration"].text)),
                    "status": self.fields[f"effect_{index}_status"].text.strip(),
                })
        ingredients = []
        for index in range(1, self.ingredient_capacity + 1):
            ingredient = self.fields[f"ingredient_{index}"].text.strip()
            if ingredient:
                ingredients.append({
                    "item": ingredient,
                    "count": max(1, _integer(self.fields[f"ingredient_{index}_count"].text, 1)),
                })
        properties = dict(self.item.properties)
        properties["durability"] = max(0, _integer(self.fields["durability"].text, 0))
        return ItemDefinition(
            item_id=self.fields["id"].text,
            name=self.fields["name"].text,
            description=self.fields["description"].text,
            category=self.category.value.lower(),
            rarity=self.rarity.value.lower(),
            icon=self.fields["icon"].text.strip(),
            max_stack=max(1, _integer(self.fields["max_stack"].text, 1)),
            value=max(0, _integer(self.fields["value"].text, 0)),
            weight=max(0.0, _number(self.fields["weight"].text, 0.0)),
            tags=[tag.strip() for tag in self.fields["tags"].text.split(",") if tag.strip()],
            usable=self.usable.checked,
            equippable=self.equippable.checked,
            equip_slot=self.fields["equip_slot"].text,
            properties=properties,
            weapon={
                "damage": max(0.0, _number(self.fields["weapon_damage"].text)),
                "attack_speed": max(0.0, _number(self.fields["weapon_speed"].text, 1.0)),
                "range": max(0.0, _number(self.fields["weapon_range"].text, 1.0)),
            },
            tool={
                "type": self.fields["tool_type"].text.strip(),
                "power": max(0.0, _number(self.fields["tool_power"].text)),
            },
            armor={
                "defense": max(0.0, _number(self.fields["armor_defense"].text)),
                "resistance": max(0.0, _number(self.fields["armor_resistance"].text)),
            },
            consumable={
                "health": _number(self.fields["consumable_health"].text),
                "stamina": _number(self.fields["consumable_stamina"].text),
                "mana": _number(self.fields["consumable_mana"].text),
            },
            requirements={
                "level": max(0, _integer(self.fields["req_level"].text)),
                "skill": self.fields["req_skill"].text.strip(),
                "skill_level": max(0, _integer(self.fields["req_skill_level"].text)),
            },
            equipment={
                "health": _number(self.fields["bonus_health"].text),
                "stamina": _number(self.fields["bonus_stamina"].text),
                "mana": _number(self.fields["bonus_mana"].text),
                "move_speed": _number(self.fields["bonus_move_speed"].text),
                "sprint_multiplier": _number(self.fields["bonus_sprint"].text),
                "sneak_multiplier": _number(self.fields["bonus_sneak"].text),
            },
            crafting={
                "station": self.fields["crafting_station"].text.strip(),
                "time": max(0.0, _number(self.fields["crafting_time"].text)),
                "output_count": max(1, _integer(self.fields["crafting_output"].text, 1)),
                "ingredients": ingredients,
            },
            loot={
                "min": max(1, _integer(self.fields["loot_min"].text, 1)),
                "max": max(1, _integer(self.fields["loot_max"].text, 1)),
                "chance": max(0.0, min(1.0, _number(self.fields["loot_chance"].text, 1.0))),
                "weight": max(0.0, _number(self.fields["loot_weight"].text, 1.0)),
                "source": self.fields["loot_source"].text.strip(),
                "table": self.fields["loot_table"].text.strip(),
                "conditions": self.fields["loot_conditions"].text.strip(),
            },
            effects=effects,
            use_action={
                "type": self.use_action.value.lower(),
                "target": self.use_target.value.lower(),
                "cooldown": max(0.0, _number(self.fields["use_cooldown"].text)),
                "animation": self.fields["use_animation"].text.strip(),
                "callbacks": {
                    key: self.fields[field_name].text.strip()
                    for key, field_name in (
                        ("use", "use_callback"),
                        ("equip", "equip_callback"),
                        ("drop", "drop_callback"),
                    )
                    if self.fields[field_name].text.strip()
                },
            },
            visuals={
                "world_sprite": self.fields["world_sprite"].text.strip(),
                "drop_sprite": self.fields["drop_sprite"].text.strip(),
            },
            audio={
                "pickup": self.fields["pickup_sound"].text.strip(),
                "use": self.fields["use_sound"].text.strip(),
                "equip": self.fields["equip_sound"].text.strip(),
                "drop": self.fields["drop_sound"].text.strip(),
            },
            shop={
                "buy_price": max(0, _integer(self.fields["shop_buy"].text)),
                "sell_price": max(0, _integer(self.fields["shop_sell"].text)),
                "stock": _integer(self.fields["shop_stock"].text, -1),
                "vendor": self.fields["shop_vendor"].text.strip(),
                "unlock_level": max(0, _integer(self.fields["shop_unlock_level"].text)),
                "currency": self.fields["shop_currency"].text.strip() or "gold",
                "can_buy": self.can_buy.checked,
                "can_sell": self.can_sell.checked,
            },
            metadata={
                "author": self.fields["author"].text.strip(),
                "guid": self.fields["guid"].text.strip(),
                "notes": self.fields["notes"].text,
            },
        )

    def _load_controls(self) -> None:
        self._loading = True
        try:
            item = self.item
            effects = item.effects or []
            ingredients = item.crafting.get("ingredients") or []
            use_action = item.use_action or {}
            visuals = item.visuals or {}
            audio = item.audio or {}
            equipment = item.equipment or {}
            shop = item.shop or {}
            metadata = item.metadata or {}
            values = {
                "id": item.item_id,
                "name": item.name,
                "description": item.description,
                "max_stack": str(item.max_stack),
                "value": str(item.value),
                "weight": f"{item.weight:g}",
                "equip_slot": item.equip_slot,
                "tags": ", ".join(item.tags),
                "icon": item.icon,
                "weapon_damage": str(item.weapon.get("damage", 0)),
                "weapon_speed": str(item.weapon.get("attack_speed", 1.0)),
                "weapon_range": str(item.weapon.get("range", 1.0)),
                "tool_type": str(item.tool.get("type", "")),
                "tool_power": str(item.tool.get("power", 0)),
                "durability": str(item.properties.get("durability", 0)),
                "armor_defense": str(item.armor.get("defense", 0)),
                "armor_resistance": str(item.armor.get("resistance", 0)),
                "consumable_health": str(item.consumable.get("health", 0)),
                "consumable_stamina": str(item.consumable.get("stamina", 0)),
                "consumable_mana": str(item.consumable.get("mana", 0)),
                "effect_type": str(item.effects[0].get("type", "")) if item.effects else "",
                "effect_value": str(item.effects[0].get("value", 0)) if item.effects else "0",
                "effect_duration": str(item.effects[0].get("duration", 0)) if item.effects else "0",
                "effect_status": str(item.effects[0].get("status", "")) if item.effects else "",
                "crafting_station": str(item.crafting.get("station", "")),
                "crafting_time": str(item.crafting.get("time", 0)),
                "crafting_output": str(item.crafting.get("output_count", 1)),
                "ingredient_1": str((item.crafting.get("ingredients") or [{}])[0].get("item", "")),
                "ingredient_1_count": str((item.crafting.get("ingredients") or [{"count": 1}])[0].get("count", 1)),
                "ingredient_2": str((item.crafting.get("ingredients") or [{}, {"item": ""}])[1].get("item", "")) if len(item.crafting.get("ingredients") or []) > 1 else "",
                "ingredient_2_count": str((item.crafting.get("ingredients") or [{}, {"count": 1}])[1].get("count", 1)) if len(item.crafting.get("ingredients") or []) > 1 else "1",
                "loot_min": str(item.loot.get("min", 1)),
                "loot_max": str(item.loot.get("max", 1)),
                "loot_chance": str(item.loot.get("chance", 1.0)),
                "loot_weight": str(item.loot.get("weight", 1.0)),
                "loot_source": str(item.loot.get("source", "")),
                "loot_table": str(item.loot.get("table", "")),
                "loot_conditions": str(item.loot.get("conditions", "")),
                "req_level": str(item.requirements.get("level", 0)),
                "req_skill": str(item.requirements.get("skill", "")),
                "req_skill_level": str(item.requirements.get("skill_level", 0)),
                "world_sprite": str(visuals.get("world_sprite", "")),
                "drop_sprite": str(visuals.get("drop_sprite", "")),
                "author": str(metadata.get("author", "")),
                "guid": str(metadata.get("guid", "")),
                "notes": str(metadata.get("notes", "")),
                "use_cooldown": str(use_action.get("cooldown", 0)),
                "use_animation": str(use_action.get("animation", "")),
                "use_callback": str((use_action.get("callbacks") or {}).get("use", use_action.get("use_callback", ""))),
                "equip_callback": str((use_action.get("callbacks") or {}).get("equip", use_action.get("equip_callback", ""))),
                "drop_callback": str((use_action.get("callbacks") or {}).get("drop", use_action.get("drop_callback", ""))),
                "pickup_sound": str(audio.get("pickup", "")),
                "use_sound": str(audio.get("use", "")),
                "equip_sound": str(audio.get("equip", "")),
                "drop_sound": str(audio.get("drop", "")),
                "bonus_health": str(equipment.get("health", 0)),
                "bonus_stamina": str(equipment.get("stamina", 0)),
                "bonus_mana": str(equipment.get("mana", 0)),
                "bonus_move_speed": str(equipment.get("move_speed", 0)),
                "bonus_sprint": str(equipment.get("sprint_multiplier", 0)),
                "bonus_sneak": str(equipment.get("sneak_multiplier", 0)),
                "shop_buy": str(shop.get("buy_price", 0)),
                "shop_sell": str(shop.get("sell_price", 0)),
                "shop_stock": str(shop.get("stock", -1)),
                "shop_vendor": str(shop.get("vendor", "")),
                "shop_unlock_level": str(shop.get("unlock_level", 0)),
                "shop_currency": str(shop.get("currency", "gold")),
            }
            for index in range(1, self.effect_capacity + 1):
                effect = effects[index - 1] if index <= len(effects) else {}
                values.update({
                    f"effect_{index}_type": str(effect.get("type", "")),
                    f"effect_{index}_value": str(effect.get("value", 0)),
                    f"effect_{index}_duration": str(effect.get("duration", 0)),
                    f"effect_{index}_status": str(effect.get("status", "")),
                })
            for index in range(1, self.ingredient_capacity + 1):
                ingredient = ingredients[index - 1] if index <= len(ingredients) else {}
                values.update({
                    f"ingredient_{index}": str(ingredient.get("item", "")),
                    f"ingredient_{index}_count": str(ingredient.get("count", 1)),
                })
            for name, value in values.items():
                self.fields[name].set_text(value)
            self.category.selected = self._option_index(self.category.options, item.category)
            self.rarity.selected = self._option_index(self.rarity.options, item.rarity)
            self.usable.checked = item.usable
            self.equippable.checked = item.equippable
            self.can_buy.checked = bool(shop.get("can_buy", True))
            self.can_sell.checked = bool(shop.get("can_sell", True))
            self.use_action.selected = self._option_index(self.use_action.options, use_action.get("type", "none"))
            self.use_target.selected = self._option_index(self.use_target.options, use_action.get("target", "self"))
        finally:
            self._loading = False

    @staticmethod
    def _option_index(options: tuple[str, ...], value: str) -> int:
        value = str(value).lower()
        for index, option in enumerate(options):
            if option.lower() == value:
                return index
        return 0

    def _field_changed(self, _value: str) -> None:
        if not self._loading:
            self.dirty = True

    def _dropdown_changed(self, _index: int, _value: str) -> None:
        if not self._loading:
            self.dirty = True

    def _check_changed(self, _value: bool) -> None:
        if not self._loading:
            self.dirty = True

    def save_item(self) -> None:
        self.item = self._collect_item()
        if not self.item.item_id:
            self.status = "Item ID is required"
            return
        problems = self._validation_problems(self.item)
        if problems:
            self.status = "Cannot save: " + ", ".join(problems)
            return
        if self.document_path is None:
            # Save creates a predictable project-local item on the first
            # press.  Save As remains available when another location or
            # filename is required.
            self.document_path = self.items_root / f"{self.item.item_id}{ITEM_ASSET_SUFFIX}"
        try:
            self.document_path = ItemAsset(self.item).save(self.document_path)
            self.dirty = False
            self.refresh_item_list()
            self.status = f"Saved {self._project_relative(self.document_path)}"
        except Exception as exc:
            self.status = f"Could not save item: {exc}"

    def _project_relative(self, path: Path) -> str:
        return self.project_context.relative_asset(path, root=self.project_path)

    def _validation_problems(self, item: ItemDefinition | None = None) -> list[str]:
        item = item or self._collect_item()
        problems: list[str] = []
        if not item.item_id:
            problems.append("missing item ID")
        elif any(character.isspace() for character in item.item_id):
            problems.append("item ID must not contain spaces")
        if not item.name:
            problems.append("missing display name")
        if item.max_stack < 1:
            problems.append("max stack must be at least 1")
        if item.loot:
            loot_min = _integer(str(item.loot.get("min", 1)), 1)
            loot_max = _integer(str(item.loot.get("max", 1)), 1)
            chance = _number(str(item.loot.get("chance", 1.0)), 1.0)
            if loot_min > loot_max:
                problems.append("loot minimum is greater than maximum")
            if not 0.0 <= chance <= 1.0:
                problems.append("loot chance must be between 0 and 1")
        if item.equippable and item.equip_slot in {"", "none"}:
            problems.append("equippable items need an equipment slot")
        action_type = str(item.use_action.get("type", "none"))
        if item.usable and action_type in {"", "none"}:
            problems.append("usable items need a use action")
        for index, ingredient in enumerate(item.crafting.get("ingredients", []), 1):
            if not ingredient.get("item"):
                problems.append(f"crafting ingredient {index} has no item ID")
            if _integer(str(ingredient.get("count", 0)), 0) < 1:
                problems.append(f"crafting ingredient {index} needs a positive count")
        if item.shop:
            if _integer(str(item.shop.get("buy_price", 0)), 0) < 0:
                problems.append("shop buy price cannot be negative")
            if _integer(str(item.shop.get("sell_price", 0)), 0) < 0:
                problems.append("shop sell price cannot be negative")
        for field_name, label in (("icon", "icon"), ("world_sprite", "world sprite"), ("drop_sprite", "drop sprite")):
            value = self.fields[field_name].text.strip()
            if value and not self._asset_path(value).is_file():
                problems.append(f"missing {label} asset: {value}")
        for field_name, label in (("pickup_sound", "pickup sound"), ("use_sound", "use sound"), ("equip_sound", "equip sound"), ("drop_sound", "drop sound")):
            value = self.fields[field_name].text.strip()
            if value and not self._asset_path(value).is_file():
                problems.append(f"missing {label} asset: {value}")
        return problems

    def validate_item(self) -> None:
        item = self._collect_item()
        problems = self._validation_problems(item)
        if problems:
            self.status = "Invalid item: " + ", ".join(problems)
        else:
            self.status = "Item is valid"

    # ------------------------------------------------------------------
    # Item browser and icon picker
    # ------------------------------------------------------------------

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

    def _open_browser(self, mode: str) -> None:
        self.modal = "browser"
        self.browser_mode = mode
        self.browser_root = self.project_path
        start = self._item_start_path() if mode in {"open", "save"} else self.assets_root
        extensions = (
            (ITEM_ASSET_SUFFIX,)
            if mode in {"open", "save"}
            else IMAGE_EXTENSIONS
        )
        self.file_browser.open(self.project_path, start=start, extensions=extensions)
        self.browser_path = self.file_browser.path
        self.browser_name.set_text(f"{self.item.item_id}{ITEM_ASSET_SUFFIX}" if mode == "save" else "")
        self._refresh_browser()

    def _refresh_browser(self) -> None:
        self.file_browser.refresh()
        self.browser_path = self.file_browser.path
        self.browser_entries = list(self.file_browser.entries)
        sync_browser_list(self.file_browser, self.browser_list)

    def _browser_selected(self, index: int) -> None:
        path = self.file_browser.select(index)
        self._refresh_browser()
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

    # ------------------------------------------------------------------
    # UI and rendering
    # ------------------------------------------------------------------

    def _menu_opened(self, opened: Menu) -> None:
        close_other_menus(self.menus, opened)

    def _show_about(self) -> None:
        self.info_title = "Nexora Item Assets"
        self.info_lines = (
            "Items are saved as versioned .nitem resources.",
            "The same data can be loaded by inventory, equipment, crafting and loot systems.",
            "Use File > Save As to create an item in the project items folder.",
        )
        self.modal = "info"

    def _layout(self) -> tuple[float, float]:
        width = float(self.game.renderer.width)
        height = float(self.game.renderer.height)
        if (width, height) == self._layout_size:
            return width, height
        self._layout_size = (width, height)
        body_top = self.TOOLBAR_HEIGHT
        body_bottom = height - self.STATUS_HEIGHT
        body_height = max(0.0, body_bottom - body_top)
        left = min(self.LEFT_WIDTH, width * 0.25)
        preview = min(self.PREVIEW_WIDTH, max(260.0, width * 0.24))
        self.left_panel = Rect(0.0, body_top, left, body_height)
        self.preview_panel = Rect(left, body_top, preview, body_height)
        self.form_panel = Rect(left + preview, body_top, max(0.0, width - left - preview), body_height)
        self._layout_controls(width, height)
        return width, height

    def _layout_controls(self, width: float, height: float) -> None:
        self.file_menu.rect = Rect(16.0, 9.0, 82.0, 40.0)
        self.item_menu.rect = Rect(105.0, 9.0, 88.0, 40.0)
        self.help_menu.rect = Rect(216.0, 9.0, 86.0, 40.0)
        self.item_search.rect = Rect(self.left_panel.x + 12.0, self.left_panel.y + 46.0, self.left_panel.width - 24.0, 34.0)
        self.item_list.rect = Rect(self.left_panel.x + 12.0, self.left_panel.y + 88.0, self.left_panel.width - 24.0, max(120.0, self.left_panel.height - 152.0))
        button_y = self.left_panel.y + self.left_panel.height - 52.0
        button_width = (self.left_panel.width - 36.0) / 3.0
        self.new_button.rect = Rect(self.left_panel.x + 12.0, button_y, button_width, 32.0)
        self.open_button.rect = Rect(self.new_button.rect.x + button_width + 6.0, button_y, button_width, 32.0)
        self.save_button.rect = Rect(self.open_button.rect.x + button_width + 6.0, button_y, button_width, 32.0)

        self.icon_preview = Rect(self.preview_panel.x + 36.0, self.preview_panel.y + 74.0, min(self.preview_panel.width - 72.0, 248.0), min(self.preview_panel.width - 72.0, 248.0))
        self.icon_button.rect = Rect(self.preview_panel.x + 36.0, self.icon_preview.y + self.icon_preview.height + 18.0, self.icon_preview.width, 34.0)

        x = self.form_panel.x + 16.0
        inner = max(240.0, self.form_panel.width - 32.0)
        gap = 10.0
        half = max(110.0, (inner - gap) / 2.0)
        field_height = 34.0
        right = x + half + gap

        content_top = self.form_panel.y + 118.0
        row = 52.0
        self._tab_layouts = {
            "General": [
                ("Item ID", "id", x, content_top, half),
                ("Display Name", "name", right, content_top, half),
                ("Description", "description", x, content_top + row, inner),
                ("Tags (comma separated)", "tags", x, content_top + row * 2.0, inner),
                ("Icon Asset", "icon", x, content_top + row * 3.0, half),
                ("World Sprite", "world_sprite", right, content_top + row * 3.0, half),
                ("Drop Sprite", "drop_sprite", x, content_top + row * 4.0, half),
                ("Author", "author", right, content_top + row * 4.0, half),
                ("GUID", "guid", x, content_top + row * 5.0, half),
                ("Editor Notes", "notes", right, content_top + row * 5.0, half),
            ],
            "Gameplay": [
                ("Max Stack", "max_stack", x, content_top, half),
                ("Value", "value", right, content_top, half),
                ("Weight", "weight", x, content_top + row, half),
                ("Equip Slot", "equip_slot", right, content_top + row, half),
                ("Durability", "durability", x, content_top + row * 2.0, half),
                ("Armor Defense", "armor_defense", right, content_top + row * 2.0, half),
                ("Armor Resistance", "armor_resistance", x, content_top + row * 3.0, half),
                ("Weapon Damage", "weapon_damage", right, content_top + row * 3.0, half),
                ("Attack Speed", "weapon_speed", x, content_top + row * 4.0, half),
                ("Weapon Range", "weapon_range", right, content_top + row * 4.0, half),
                ("Tool Type", "tool_type", x, content_top + row * 5.0, half),
                ("Tool Power", "tool_power", right, content_top + row * 5.0, half),
                ("Health Bonus", "bonus_health", x, content_top + row * 6.0, half),
                ("Stamina Bonus", "bonus_stamina", right, content_top + row * 6.0, half),
                ("Mana Bonus", "bonus_mana", x, content_top + row * 7.0, half),
                ("Move Speed Bonus", "bonus_move_speed", right, content_top + row * 7.0, half),
                ("Sprint Multiplier", "bonus_sprint", x, content_top + row * 8.0, half),
                ("Sneak Multiplier", "bonus_sneak", right, content_top + row * 8.0, half),
            ],
            "Use": [
                ("Cooldown (seconds)", "use_cooldown", x, content_top + row, half),
                ("Use Animation", "use_animation", right, content_top + row, half),
                ("Pickup Sound", "pickup_sound", x, content_top + row * 2.0, half),
                ("Use Sound", "use_sound", right, content_top + row * 2.0, half),
                ("Equip Sound", "equip_sound", x, content_top + row * 3.0, half),
                ("Drop Sound", "drop_sound", right, content_top + row * 3.0, half),
                ("Use Callback ID", "use_callback", x, content_top + row * 4.0, half),
                ("Equip Callback ID", "equip_callback", right, content_top + row * 4.0, half),
                ("Drop Callback ID", "drop_callback", x, content_top + row * 5.0, half),
            ],
            "Effects": [],
            "Crafting": [
                ("Crafting Station", "crafting_station", x, content_top, half),
                ("Crafting Time (seconds)", "crafting_time", right, content_top, half),
                ("Output Count", "crafting_output", x, content_top + row, half),
            ],
            "Loot": [
                ("Minimum Quantity", "loot_min", x, content_top, half),
                ("Maximum Quantity", "loot_max", right, content_top, half),
                ("Drop Chance (0-1)", "loot_chance", x, content_top + row, half),
                ("Drop Weight", "loot_weight", right, content_top + row, half),
                ("Drop Source", "loot_source", x, content_top + row * 2.0, inner),
                ("Required Level", "req_level", x, content_top + row * 3.0, half),
                ("Required Skill", "req_skill", right, content_top + row * 3.0, half),
                ("Required Skill Level", "req_skill_level", x, content_top + row * 4.0, half),
                ("Loot Table", "loot_table", x, content_top + row * 5.0, half),
                ("Drop Conditions", "loot_conditions", right, content_top + row * 5.0, half),
            ],
            "Shop": [
                ("Buy Price", "shop_buy", x, content_top, half),
                ("Sell Price", "shop_sell", right, content_top, half),
                ("Stock (-1 = unlimited)", "shop_stock", x, content_top + row, half),
                ("Vendor Category", "shop_vendor", right, content_top + row, half),
                ("Unlock Level", "shop_unlock_level", x, content_top + row * 2.0, half),
                ("Currency", "shop_currency", right, content_top + row * 2.0, half),
            ],
        }
        for index in range(1, self.effect_capacity + 1):
            base_y = content_top + index * 70.0
            self._tab_layouts["Effects"].extend([
                (f"Effect {index} Type", f"effect_{index}_type", x, base_y, half),
                ("Value", f"effect_{index}_value", right, base_y, half),
                ("Duration", f"effect_{index}_duration", x, base_y + 52.0, half),
                ("Status", f"effect_{index}_status", right, base_y + 52.0, half),
            ])
        for index in range(1, self.ingredient_capacity + 1):
            base_y = content_top + 122.0 + (index - 1) * 52.0
            self._tab_layouts["Crafting"].extend([
                (f"Ingredient {index}", f"ingredient_{index}", x, base_y, half),
                ("Count", f"ingredient_{index}_count", right, base_y, half),
            ])
        for specs in self._tab_layouts.values():
            for _label, name, field_x, label_y, field_width in specs:
                self.fields[name].rect = Rect(field_x, label_y + 18.0, field_width, field_height)

        tab_x = self.form_panel.x + 166.0
        tab_y = self.form_panel.y + 10.0
        columns = 4
        tab_width = min(112.0, max(78.0, (self.form_panel.width - 182.0) / columns))
        for index, button in enumerate(self.tab_buttons):
            column = index % columns
            row_index = index // columns
            button.rect = Rect(tab_x + column * (tab_width + 6.0), tab_y + row_index * 38.0, tab_width, 34.0)
            button.selected = button.text == self.active_tab

        self.category.rect = Rect(x, content_top + row * 6.0, half, field_height)
        self.rarity.rect = Rect(right, content_top + row * 6.0, half, field_height)
        self.usable.rect = Rect(x, content_top + row * 9.0, 130.0, 30.0)
        self.equippable.rect = Rect(x + 142.0, content_top + row * 9.0, 150.0, 30.0)
        self.can_buy.rect = Rect(x, content_top + row * 4.0, 120.0, 30.0)
        self.can_sell.rect = Rect(x + 132.0, content_top + row * 4.0, 120.0, 30.0)
        self.use_action.rect = Rect(x, content_top, half, field_height)
        self.use_target.rect = Rect(right, content_top, half, field_height)

        self._layout_modal_controls(width, height)

    def _layout_modal_controls(self, width: float, height: float) -> None:
        browser_window = Rect(150.0, 76.0, width - 300.0, height - 152.0)
        inner_x = browser_window.x + 18.0
        inner_right = browser_window.x + browser_window.width - 18.0
        footer_y = browser_window.y + browser_window.height - 50.0
        self.browser_list.rect = Rect(inner_x, browser_window.y + 78.0, max(220.0, browser_window.width - 36.0), max(100.0, browser_window.height - 128.0))
        if self.browser_mode == "save":
            self.browser_cancel_button.rect = Rect(inner_right - 212.0, footer_y, 100.0, 32.0)
            self.browser_save_button.rect = Rect(inner_right - 100.0, footer_y, 100.0, 32.0)
        else:
            self.browser_cancel_button.rect = Rect(inner_right - 100.0, footer_y, 100.0, 32.0)
            self.browser_save_button.rect = Rect(inner_right - 100.0, footer_y, 100.0, 32.0)
        self.browser_name.rect = Rect(inner_x, footer_y, max(180.0, self.browser_cancel_button.rect.x - inner_x - 14.0), 32.0)
        info_window = centered_rect((width, height), 660.0, 340.0)
        self.info_close_button.rect = Rect(info_window.x + info_window.width - 126.0, info_window.y + info_window.height - 52.0, 108.0, 32.0)

    def _update_controls(self, controls: list, mouse_x: float, mouse_y: float) -> None:
        for control in controls:
            if control.update(self.game.input, mouse_x, mouse_y):
                break

    def update(self, delta_time: float) -> None:
        del delta_time
        width, height = self._layout()
        mouse_x, mouse_y = self.game.input.mouse_position
        if self.modal == "browser":
            controls = [self.browser_list, self.browser_cancel_button]
            if self.browser_mode == "save":
                controls.extend((self.browser_name, self.browser_save_button))
            self._update_controls(controls, mouse_x, mouse_y)
            return
        if self.modal == "info":
            self._update_controls([self.info_close_button], mouse_x, mouse_y)
            return
        menu_was_open = any(menu.open for menu in self.menus)
        self._update_controls(self.menus, mouse_x, mouse_y)
        if menu_was_open or any(menu.open for menu in self.menus):
            return
        controls = [
            self.item_search,
            self.item_list,
            self.new_button,
            self.open_button,
            self.save_button,
            self.icon_button,
            *self.tab_buttons,
        ]
        if self.active_tab == "General":
            controls.extend((self.category, self.rarity))
        elif self.active_tab == "Gameplay":
            controls.extend((self.usable, self.equippable))
        elif self.active_tab == "Use":
            controls.extend((self.use_action, self.use_target))
        elif self.active_tab == "Shop":
            controls.extend((self.can_buy, self.can_sell))
        active_fields = {name for _label, name, _x, _y, _width in self._tab_layouts.get(self.active_tab, ())}
        controls.extend(self.fields[name] for name in active_fields)
        self._update_controls(controls, mouse_x, mouse_y)
        del width, height

    def _draw_label(self, renderer, text: str, x: float, y: float, viewport_size: tuple[float, float]) -> None:
        draw_text(renderer, text, x, y, viewport_size, scale=0.44, color=self.theme.muted)

    def _render_form(self, renderer, viewport_size: tuple[float, float]) -> None:
        for label, name, field_x, label_y, _field_width in self._tab_layouts.get(self.active_tab, ()):
            self._draw_label(renderer, label, field_x, label_y, viewport_size)
            self.fields[name].render(renderer, viewport_size, self.theme)
        if self.active_tab == "General":
            self._draw_label(renderer, "Category", self.category.rect.x, self.category.rect.y - 18.0, viewport_size)
            self.category.render(renderer, viewport_size, self.theme)
            self._draw_label(renderer, "Rarity", self.rarity.rect.x, self.rarity.rect.y - 18.0, viewport_size)
            self.rarity.render(renderer, viewport_size, self.theme)
        elif self.active_tab == "Gameplay":
            self.usable.render(renderer, viewport_size, self.theme)
            self.equippable.render(renderer, viewport_size, self.theme)
        elif self.active_tab == "Use":
            self._draw_label(renderer, "Use Action", self.use_action.rect.x, self.use_action.rect.y - 18.0, viewport_size)
            self.use_action.render(renderer, viewport_size, self.theme)
            self._draw_label(renderer, "Target", self.use_target.rect.x, self.use_target.rect.y - 18.0, viewport_size)
            self.use_target.render(renderer, viewport_size, self.theme)
        elif self.active_tab == "Shop":
            self.can_buy.render(renderer, viewport_size, self.theme)
            self.can_sell.render(renderer, viewport_size, self.theme)

    def _render_main(self, renderer, viewport_size: tuple[float, float]) -> None:
        width, height = viewport_size
        draw_rect(renderer, Rect(0, 0, width, self.TOOLBAR_HEIGHT), self.theme.panel, viewport_size)
        draw_rect(renderer, self.left_panel, self.theme.panel, viewport_size)
        draw_rect(renderer, self.preview_panel, self.theme.panel_dark, viewport_size)
        draw_rect(renderer, self.form_panel, self.theme.panel, viewport_size)
        draw_rect(renderer, Rect(0, height - self.STATUS_HEIGHT, width, self.STATUS_HEIGHT), self.theme.panel, viewport_size)
        for rect in (Rect(0, 0, width, self.TOOLBAR_HEIGHT), self.left_panel, self.preview_panel, self.form_panel):
            draw_outline(renderer, rect, self.theme.border, viewport_size)

        draw_text(renderer, f"{self.item.name}{' *' if self.dirty else ''}", width - 16.0, 18.0, viewport_size, scale=0.62, color=self.theme.muted, align="right")
        draw_text(renderer, "Items", self.left_panel.x + 12.0, self.left_panel.y + 14.0, viewport_size, scale=0.76)
        draw_text(renderer, "Preview", self.preview_panel.x + 16.0, self.preview_panel.y + 14.0, viewport_size, scale=0.76)
        draw_text(renderer, "Item Properties", self.form_panel.x + 16.0, self.form_panel.y + 14.0, viewport_size, scale=0.76)
        draw_text(renderer, self.status, 12.0, height - self.STATUS_HEIGHT + 7.0, viewport_size, scale=0.56, color=self.theme.muted)
        draw_text(renderer, "Nexora Item Editor", width - 12.0, height - self.STATUS_HEIGHT + 7.0, viewport_size, scale=0.56, color=self.theme.muted, align="right")

        self.item_search.render(renderer, viewport_size, self.theme)
        self.item_list.render(renderer, viewport_size, self.theme)
        for button in (self.new_button, self.open_button, self.save_button):
            button.render(renderer, viewport_size, self.theme)
        for menu in self.menus:
            menu.render(renderer, viewport_size, self.theme)
        for button in self.tab_buttons:
            button.render(renderer, viewport_size, self.theme)

        draw_rect(renderer, self.icon_preview, self.theme.input, viewport_size, radius=5.0)
        draw_outline(renderer, self.icon_preview, self.theme.border, viewport_size)
        if self.icon_texture is not None:
            center_x, center_y = self.icon_preview.center()
            sprite_x = center_x - width / 2.0
            sprite_y = center_y - height / 2.0
            size = min(self.icon_preview.width - 28.0, self.icon_preview.height - 28.0)
            renderer.sprite(self.icon_texture, sprite_x, sprite_y, width=size, height=size)
        else:
            draw_text(renderer, "No icon", *self.icon_preview.center(), viewport_size, scale=0.62, color=self.theme.muted, align="center")
        self.icon_button.render(renderer, viewport_size, self.theme)
        self._render_form(renderer, viewport_size)

    def _render_browser(self, renderer, viewport_size: tuple[float, float]) -> None:
        width, height = viewport_size
        draw_rect(renderer, Rect(0, 0, width, height), (0, 0, 0, 175), viewport_size)
        window = Rect(150.0, 76.0, width - 300.0, height - 152.0)
        draw_rect(renderer, window, self.theme.panel, viewport_size, radius=6.0)
        draw_outline(renderer, window, self.theme.border, viewport_size)
        title = {"open": "Open Item", "save": "Save Item As", "icon": "Choose Item Icon"}[self.browser_mode]
        draw_text(renderer, title, window.x + 18.0, window.y + 16.0, viewport_size, scale=0.80)
        draw_text(renderer, str(self.browser_path), window.x + 18.0, window.y + 50.0, viewport_size, scale=0.48, color=self.theme.muted)
        self.browser_list.render(renderer, viewport_size, self.theme)
        self.browser_cancel_button.render(renderer, viewport_size, self.theme)
        if self.browser_mode == "save":
            draw_text(renderer, "File name", window.x + 18.0, window.y + window.height - 72.0, viewport_size, scale=0.48, color=self.theme.muted)
            self.browser_name.render(renderer, viewport_size, self.theme)
            self.browser_save_button.render(renderer, viewport_size, self.theme)

    def _render_info(self, renderer, viewport_size: tuple[float, float]) -> None:
        width, height = viewport_size
        draw_rect(renderer, Rect(0, 0, width, height), (0, 0, 0, 175), viewport_size)
        window = centered_rect(viewport_size, 660.0, 340.0)
        draw_rect(renderer, window, self.theme.panel, viewport_size, radius=6.0)
        draw_outline(renderer, window, self.theme.border, viewport_size)
        draw_text(renderer, self.info_title, window.x + 22.0, window.y + 20.0, viewport_size, scale=0.86)
        y = window.y + 78.0
        for line in self.info_lines:
            draw_text(renderer, line, window.x + 24.0, y, viewport_size, scale=0.60, color=self.theme.text)
            y += 38.0
        self.info_close_button.render(renderer, viewport_size, self.theme)

    def render(self, interpolation: float) -> None:
        del interpolation
        width, height = self._layout()
        renderer = self.game.renderer
        viewport_size = (width, height)
        draw_rect(renderer, Rect(0, 0, width, height), self.theme.background, viewport_size)
        with renderer.overlay_scope():
            self._render_main(renderer, viewport_size)
            if self.modal == "browser":
                self._render_browser(renderer, viewport_size)
            elif self.modal == "info":
                self._render_info(renderer, viewport_size)

    def _close_modal(self) -> None:
        self.modal = None


class ItemEditorApp(Game):
    """Application wrapper for the standalone Item Editor."""

    def __init__(self, *, project_path: str | Path | None = None, item_path: str | Path | None = None) -> None:
        self.item_project_path = resolve_project_path(project_path)
        self.item_project_context = EditorProjectContext.from_path(self.item_project_path)
        self.item_asset_path = item_path
        super().__init__(
            project_name="NexoraStandaloneItemEditor",
            title=f"Nexora Item Editor - {self.item_project_path.name}",
            width=1440,
            height=900,
            resizable=True,
            editor_mode=True,
        )
        self.editor_scene = None

    def initialize(self) -> None:
        if self.engine is not None:
            self.engine.assets.root = self.item_project_context.assets_root
        icon_path = self.item_project_context.icon_path
        if self.window is not None and icon_path.is_file():
            try:
                self.window.set_icon(icon_path)
            except Exception:
                pass
        self.editor_scene = ItemEditorScene(
            self,
            self.item_project_path,
            self.item_asset_path,
            self.item_project_context,
        )
        self.scene = self.editor_scene


def run_item_editor(project_path: str | Path | None = None, item_path: str | Path | None = None) -> int:
    try:
        ItemEditorApp(project_path=project_path, item_path=item_path).run()
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"[Nexora Item Editor] {exc}")
        return 2
    return 0


__all__ = ["ItemEditorApp", "ItemEditorScene", "run_item_editor"]
