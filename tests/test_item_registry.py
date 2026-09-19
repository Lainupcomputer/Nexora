from __future__ import annotations

from pathlib import Path

from nexora.items import ItemAsset, ItemCallbackRegistry, ItemDefinition, ItemRegistry


def test_item_registry_loads_default_and_custom_paths_with_override(tmp_path: Path) -> None:
    base = tmp_path / "items"
    mod = tmp_path / "mods" / "items"
    base.mkdir(parents=True)
    mod.mkdir(parents=True)
    ItemAsset(ItemDefinition(item_id="ore", name="Base Ore")).save(base / "ore")
    ItemAsset(ItemDefinition(item_id="ore", name="Mod Ore")).save(mod / "ore")
    ItemAsset(ItemDefinition(item_id="gem", name="Gem")).save(mod / "gem")

    registry = ItemRegistry(tmp_path, item_paths=[mod])
    loaded = registry.load_all()

    assert {resource.item.item_id for resource in loaded} == {"ore", "gem"}
    assert registry.require("ore").item.name == "Mod Ore"
    assert registry.duplicates[0][0] == "ore"


def test_item_registry_resolves_callback_ids() -> None:
    callbacks = ItemCallbackRegistry()
    callback = lambda *_args: "ok"
    callbacks.register("consume_test", callback)
    assert callbacks.resolve("consume_test") is callback
