from __future__ import annotations

from pathlib import Path
from typing import Any

from nexora.data import DataFile, DataType, load_file, save_file

VERSION = 1


def encode(asset) -> dict[str, Any]:
    return asset.to_state()


def decode(state: Any):
    from nexora.tilemap.asset import TileMapAsset

    if not isinstance(state, dict):
        raise ValueError("Invalid Nexora TileMap data.")
    return TileMapAsset.from_state(dict(state))


def save(asset, path: str | Path, *, max_file_size: int) -> Path:
    return save_file(
        path,
        DataFile(DataType.TileMap, VERSION, encode(asset)),
        max_file_size=max_file_size,
    )


def load(path: str | Path, *, max_file_size: int):
    document = load_file(
        path,
        expected_type=DataType.TileMap,
        max_file_size=max_file_size,
    )
    if document.version != VERSION:
        raise ValueError(f"Unsupported Nexora TileMap data version: {document.version}")
    return decode(document.data)
