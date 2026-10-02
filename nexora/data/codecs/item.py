from __future__ import annotations

from pathlib import Path
from typing import Any

from nexora.data import DataFile, DataType, load_file, save_file

VERSION = 1


def encode(item_asset) -> dict[str, Any]:
    return item_asset.to_state()


def decode(state: Any):
    from nexora.items.asset import ItemAsset, ItemDefinition

    if not isinstance(state, dict) or not isinstance(state.get("item"), dict):
        raise ValueError("Invalid Nexora Item data.")
    return ItemAsset.from_state(dict(state))


def save(item_asset, path: str | Path, *, max_file_size: int) -> Path:
    return save_file(
        path,
        DataFile(DataType.Item, VERSION, encode(item_asset)),
        max_file_size=max_file_size,
    )


def load(path: str | Path, *, max_file_size: int):
    document = load_file(
        path,
        expected_type=DataType.Item,
        max_file_size=max_file_size,
    )
    if document.version != VERSION:
        raise ValueError(f"Unsupported Nexora Item data version: {document.version}")
    return decode(document.data)
