from __future__ import annotations

from pathlib import Path

from nexora.items import ItemAsset, ItemDefinition


def test_item_asset_roundtrip_uses_nitem_suffix(tmp_path: Path) -> None:
    item = ItemDefinition(
        item_id="iron_sword",
        name="Iron Sword",
        description="A reliable starter weapon.",
        category="weapon",
        rarity="common",
        icon="items/icons/iron_sword.png",
        max_stack=1,
        value=125,
        weight=2.5,
        tags=["weapon", "metal"],
        equippable=True,
        equip_slot="main_hand",
        weapon={"damage": 12, "attack_speed": 1.2, "range": 1.0},
        armor={"defense": 3, "resistance": 1},
        consumable={"health": 5},
        requirements={"level": 4, "skill": "smithing", "skill_level": 2},
        crafting={"station": "anvil", "time": 3.5, "output_count": 2, "ingredients": [{"item": "iron", "count": 2}]},
        loot={"min": 1, "max": 2, "chance": 0.5, "weight": 2.0, "source": "chest", "table": "rare_chest", "conditions": "level>=4"},
        effects=[{"type": "sharpness", "value": 2, "duration": 10}],
        use_action={"type": "consume", "target": "self", "cooldown": 2.0},
        equipment={"sprint_multiplier": 1.1, "sneak_multiplier": 0.9},
        visuals={"world_sprite": "items/iron_sword_world.png"},
        audio={"equip": "audio/equip.wav"},
        shop={"buy_price": 200, "sell_price": 80, "stock": -1, "can_buy": True, "can_sell": True},
        metadata={"author": "Nexora", "guid": "iron-sword-guid"},
        properties={"durability": 40},
    )

    path = ItemAsset(item).save(tmp_path / "iron_sword")
    assert path.read_bytes().startswith(b"NXDATA01")
    loaded = ItemAsset.load(path).item

    assert path.name == "iron_sword.nitem"
    assert loaded.item_id == "iron_sword"
    assert loaded.name == "Iron Sword"
    assert loaded.weapon["damage"] == 12
    assert loaded.tags == ["weapon", "metal"]
    assert loaded.armor["defense"] == 3
    assert loaded.crafting["ingredients"][0]["count"] == 2
    assert loaded.crafting["output_count"] == 2
    assert loaded.loot["chance"] == 0.5
    assert loaded.loot["table"] == "rare_chest"
    assert loaded.effects[0]["type"] == "sharpness"
    assert loaded.use_action["type"] == "consume"
    assert loaded.equipment["sprint_multiplier"] == 1.1
    assert loaded.visuals["world_sprite"].endswith("world.png")
    assert loaded.audio["equip"].endswith("equip.wav")
    assert loaded.shop["buy_price"] == 200
    assert loaded.metadata["author"] == "Nexora"
    assert loaded.properties["durability"] == 40


def test_item_asset_rejects_wrong_format() -> None:
    try:
        ItemAsset.from_state({"format": "not_nexora_item", "version": 1})
    except ValueError as exc:
        assert "Nexora Item" in str(exc)
    else:
        raise AssertionError("wrong item format was accepted")


def test_item_asset_rejects_legacy_json_nitem(tmp_path: Path) -> None:
    path = tmp_path / "legacy.nitem"
    path.write_text(
        '{"format":"nexora_item","version":1,"item":{"id":"legacy_item"}}',
        encoding="utf-8",
    )
    try:
        ItemAsset.load(path)
    except Exception:
        pass
    else:
        raise AssertionError("Legacy JSON .nitem file was accepted")
