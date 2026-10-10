from __future__ import annotations

"""Portable item resources.

``.nitem`` files intentionally contain data only.  Runtime systems such as
inventory, equipment, crafting and loot can load the same resource without
depending on the standalone editor.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ITEM_ASSET_VERSION = 1
ITEM_ASSET_SUFFIX = ".nitem"
ITEM_ASSET_MAX_PAYLOAD = 16 * 1024 * 1024


def _clean_string(value: Any, fallback: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text or fallback


def _clean_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _clean_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


@dataclass(slots=True)
class ItemDefinition:
    """Editor- and runtime-facing definition of one item."""

    item_id: str = "new_item"
    name: str = "New Item"
    description: str = ""
    category: str = "misc"
    rarity: str = "common"
    icon: str = ""
    max_stack: int = 1
    value: int = 0
    weight: float = 0.0
    tags: list[str] = field(default_factory=list)
    usable: bool = False
    equippable: bool = False
    equip_slot: str = "none"
    weapon: dict[str, Any] = field(default_factory=dict)
    tool: dict[str, Any] = field(default_factory=dict)
    armor: dict[str, Any] = field(default_factory=dict)
    consumable: dict[str, Any] = field(default_factory=dict)
    requirements: dict[str, Any] = field(default_factory=dict)
    crafting: dict[str, Any] = field(default_factory=dict)
    loot: dict[str, Any] = field(default_factory=dict)
    effects: list[dict[str, Any]] = field(default_factory=list)
    use_action: dict[str, Any] = field(default_factory=dict)
    equipment: dict[str, Any] = field(default_factory=dict)
    visuals: dict[str, Any] = field(default_factory=dict)
    audio: dict[str, Any] = field(default_factory=dict)
    shop: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.item_id = _clean_string(self.item_id, "new_item")
        self.name = _clean_string(self.name, "New Item")
        self.description = str(self.description or "")
        self.category = _clean_string(self.category, "misc").lower()
        self.rarity = _clean_string(self.rarity, "common").lower()
        self.icon = str(self.icon or "")
        self.max_stack = max(1, _clean_int(self.max_stack, 1))
        self.value = max(0, _clean_int(self.value, 0))
        self.weight = max(0.0, _clean_number(self.weight, 0.0))
        self.tags = [str(tag).strip() for tag in self.tags if str(tag).strip()]
        self.equip_slot = _clean_string(self.equip_slot, "none").lower()
        self.weapon = dict(self.weapon or {})
        self.tool = dict(self.tool or {})
        self.armor = dict(self.armor or {})
        self.consumable = dict(self.consumable or {})
        self.requirements = dict(self.requirements or {})
        self.crafting = dict(self.crafting or {})
        self.loot = dict(self.loot or {})
        self.effects = [dict(effect) for effect in self.effects if isinstance(effect, dict)]
        self.use_action = dict(self.use_action or {})
        self.equipment = dict(self.equipment or {})
        self.visuals = dict(self.visuals or {})
        self.audio = dict(self.audio or {})
        self.shop = dict(self.shop or {})
        self.metadata = dict(self.metadata or {})
        self.properties = dict(self.properties or {})

    def to_state(self) -> dict[str, Any]:
        return {
            "id": self.item_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "rarity": self.rarity,
            "icon": self.icon,
            "max_stack": self.max_stack,
            "value": self.value,
            "weight": self.weight,
            "tags": list(self.tags),
            "usable": self.usable,
            "equippable": self.equippable,
            "equip_slot": self.equip_slot,
            "weapon": dict(self.weapon),
            "tool": dict(self.tool),
            "armor": dict(self.armor),
            "consumable": dict(self.consumable),
            "requirements": dict(self.requirements),
            "crafting": dict(self.crafting),
            "loot": dict(self.loot),
            "effects": [dict(effect) for effect in self.effects],
            "use_action": dict(self.use_action),
            "equipment": dict(self.equipment),
            "visuals": dict(self.visuals),
            "audio": dict(self.audio),
            "shop": dict(self.shop),
            "metadata": dict(self.metadata),
            "properties": dict(self.properties),
        }

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "ItemDefinition":
        if not isinstance(state, dict):
            raise ValueError("Item payload must be an object.")
        return cls(
            item_id=state.get("id", state.get("item_id", "new_item")),
            name=state.get("name", "New Item"),
            description=state.get("description", ""),
            category=state.get("category", "misc"),
            rarity=state.get("rarity", "common"),
            icon=state.get("icon", ""),
            max_stack=state.get("max_stack", 1),
            value=state.get("value", 0),
            weight=state.get("weight", 0.0),
            tags=list(state.get("tags", [])),
            usable=bool(state.get("usable", False)),
            equippable=bool(state.get("equippable", False)),
            equip_slot=state.get("equip_slot", "none"),
            weapon=dict(state.get("weapon", {})),
            tool=dict(state.get("tool", {})),
            armor=dict(state.get("armor", {})),
            consumable=dict(state.get("consumable", {})),
            requirements=dict(state.get("requirements", {})),
            crafting=dict(state.get("crafting", {})),
            loot=dict(state.get("loot", {})),
            effects=list(state.get("effects", [])),
            use_action=dict(state.get("use_action", {})),
            equipment=dict(state.get("equipment", {})),
            visuals=dict(state.get("visuals", {})),
            audio=dict(state.get("audio", {})),
            shop=dict(state.get("shop", {})),
            metadata=dict(state.get("metadata", {})),
            properties=dict(state.get("properties", {})),
        )


class ItemAsset:
    """Versioned Nexora data-backed ``.nitem`` resource."""

    def __init__(self, item: ItemDefinition | None = None) -> None:
        self.item = item or ItemDefinition()

    def to_state(self) -> dict[str, Any]:
        return {"item": self.item.to_state()}

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "ItemAsset":
        if not isinstance(state, dict) or not isinstance(state.get("item"), dict):
            raise ValueError("Payload is not Nexora Item data.")
        return cls(ItemDefinition.from_state(dict(state["item"])))

    def save(self, path: str | Path) -> Path:
        from nexora.data.codecs import item as item_codec

        target = Path(path).expanduser()
        if not str(target).lower().endswith(ITEM_ASSET_SUFFIX):
            target = Path(str(target) + ITEM_ASSET_SUFFIX)
        return item_codec.save(
            self,
            target,
            max_file_size=ITEM_ASSET_MAX_PAYLOAD,
        )

    @classmethod
    def load(cls, path: str | Path) -> "ItemAsset":
        from nexora.data.codecs import item as item_codec

        return item_codec.load(
            path,
            max_file_size=ITEM_ASSET_MAX_PAYLOAD,
        )


__all__ = [
    "ITEM_ASSET_VERSION",
    "ITEM_ASSET_SUFFIX",
    "ItemDefinition",
    "ItemAsset",
]
