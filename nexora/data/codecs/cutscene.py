from __future__ import annotations

from pathlib import Path
from typing import Any

from nexora.data import DataFile, DataType, load_file, save_file

VERSION = 1


def encode(asset) -> dict[str, Any]:
    return asset.to_state()


def decode(state: Any):
    from nexora.cutscene.asset import CutsceneAsset

    if not isinstance(state, dict):
        raise ValueError("Invalid Nexora Cutscene data.")
    return CutsceneAsset.from_state(dict(state))


def save(
    asset,
    path: str | Path,
    *,
    signing_key: bytes | str,
    max_file_size: int,
) -> Path:
    return save_file(
        path,
        DataFile(DataType.Cutscene, VERSION, encode(asset)),
        signing_key=signing_key,
        max_file_size=max_file_size,
    )


def load(
    path: str | Path,
    *,
    signing_key: bytes | str,
    max_file_size: int,
):
    document = load_file(
        path,
        expected_type=DataType.Cutscene,
        signing_key=signing_key,
        max_file_size=max_file_size,
    )
    if document.version != VERSION:
        raise ValueError(f"Unsupported Nexora Cutscene data version: {document.version}")
    return decode(document.data)
