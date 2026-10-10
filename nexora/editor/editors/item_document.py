from __future__ import annotations

from pathlib import Path

from nexora.gameplay.items import ITEM_ASSET_SUFFIX, ItemAsset, ItemDefinition


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


class ItemDocumentMixin:

    def _item_start_path(self) -> Path:
        return self.project_context.items_root if self.items_root.is_dir() else self.project_path

    def _resolve_requested_path(self, value: str | Path) -> Path:
        return self._project_file_path(
            value,
            roots=(self.items_root,),
            include_assets=True,
        )

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
